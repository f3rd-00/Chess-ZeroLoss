import msvcrt
import os
import re
import time
from pathlib import Path

import chess
import chess.engine
from selenium import webdriver
from selenium.common.exceptions import (
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By


BASE_DIR = Path(__file__).resolve().parent
PROFILE = BASE_DIR / "chesscom-selenium-profile"
ENGINE_PATH = (
    BASE_DIR
    / "stockfish-windosws-x86-64-universal"
    / "stockfish"
    / "stockfish-windows-x86-64-universal.exe"
)
MOVE_RE = re.compile(
    r"^(?:[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|O-O-O|O-O)[+#]?$"
)
ENGINE_MOVE_DELAY = 1.0
SQUARE_CLICK_GAP = 0.25
BOARD_UPDATE_WAIT = 0.8
POLL_INTERVAL = 0.1
STATUS_INTERVAL = 5.0


def f3_pressed():
    pressed = False
    while msvcrt.kbhit():
        key = msvcrt.getch()
        if key in (b"\x00", b"\xe0"):
            pressed = msvcrt.getch() == b"\x3d" or pressed
    return pressed


def ask_engine_color():
    while True:
        color = input("Qual cor o motor vai jogar? (brancas/pretas): ").strip().lower()
        if color in ("brancas", "branca", "white", "w"):
            return chess.WHITE, "white"
        if color in ("pretas", "preta", "black", "p"):
            return chess.BLACK, "black"
        print("Informe 'brancas' ou 'pretas'.")


def click_square(driver, square_index, engine_turn):
    board = driver.find_element(By.CSS_SELECTOR, "wc-chess-board")
    rect = driver.execute_script(
        "const r=arguments[0].getBoundingClientRect();"
        "return {width:r.width,height:r.height};",
        board,
    )
    size = min(rect["width"], rect["height"]) / 8
    file_index = chess.square_file(square_index)
    rank_index = chess.square_rank(square_index)
    if engine_turn == chess.WHITE:
        col, row = file_index, 7 - rank_index
    else:
        col, row = 7 - file_index, rank_index

    x_offset = (col + 0.5) * size - rect["width"] / 2
    y_offset = (row + 0.5) * size - rect["height"] / 2
    ActionChains(driver).move_to_element_with_offset(
        board, x_offset, y_offset
    ).click().perform()


def choose_promotion_piece(driver, promotion, engine_turn):
    piece_names = {
        "q": "queen",
        "r": "rook",
        "b": "bishop",
        "n": "knight",
    }
    letter = promotion.lower()
    color_prefix = "w" if engine_turn == chess.WHITE else "b"
    expected = {letter, piece_names[letter], color_prefix + letter}
    deadline = time.monotonic() + 5

    while time.monotonic() < deadline:
        try:
            candidates = driver.find_elements(
                By.CSS_SELECTOR,
                ".promotion-piece, [class*='promotion']",
            )
            visible = [element for element in candidates if element.is_displayed()]
            for element in visible:
                class_value = element.get_attribute("class") or ""
                tokens = set(re.split(r"[^a-z0-9]+", class_value.lower()))
                values = [
                    element.get_attribute(attr) or ""
                    for attr in ("data-piece", "data-piece-type", "aria-label", "title")
                ]
                values.extend(tokens)
                normalized = {
                    re.sub(r"[^a-z0-9]", "", value.lower()) for value in values if value
                }
                if expected.intersection(normalized) or any(
                    f"promotionpiece{item}" in value
                    for value in normalized
                    for item in expected
                ):
                    element.click()
                    return

            piece_elements = [
                element
                for element in visible
                if "promotion-piece" in (element.get_attribute("class") or "").lower()
            ]
            if len(piece_elements) >= 4:
                index = {"q": 0, "r": 1, "b": 2, "n": 3}[letter]
                piece_elements[index].click()
                return
        except StaleElementReferenceException:
            pass
        time.sleep(0.1)

    if letter == "q":
        return
    raise TimeoutException(
        f"O seletor de promoção não apareceu para escolher {piece_names[letter]}"
    )


def play_engine_move(position):
    with chess.engine.SimpleEngine.popen_uci(str(ENGINE_PATH)) as engine:
        return engine.play(position, chess.engine.Limit(time=0.5)).move


def read_live_board(driver):
    try:
        fen = driver.execute_script(
            "const b=document.querySelector('wc-chess-board');"
            "if(!b || !b.game) return null;"
            "if(typeof b.game.getFEN==='function') return b.game.getFEN();"
            "return typeof b.game.fen==='function' ? b.game.fen() : b.game.fen || null;"
        )
        return chess.Board(fen) if isinstance(fen, str) and fen.strip() else None
    except (JavascriptException, ValueError, WebDriverException):
        return None


def main():
    if not ENGINE_PATH.is_file():
        print(f"Não encontrei o motor local: {ENGINE_PATH}")
        return

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE}")
    options.add_argument("--start-maximized")
    options.page_load_strategy = "eager"

    driver = None
    try:
        print("Abrindo o Chrome com Selenium...")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        try:
            driver.get("https://www.chess.com/")
        except TimeoutException:
            print("A navegação demorou; mantendo a página aberta para terminar de carregar.")

        print(f"Navegador pronto: {driver.current_url}")
        print(f"Título: {driver.title}")
        print("Faça login e abra a partida nesta janela do Chrome. Aguardando o tabuleiro...")
        while True:
            try:
                boards = driver.find_elements(By.CSS_SELECTOR, "wc-chess-board")
                if any(board.is_displayed() for board in boards):
                    break
            except (StaleElementReferenceException, WebDriverException):
                pass
            time.sleep(0.5)

        engine_turn, engine_color = ask_engine_color()

        print("Observando os lances. Você joga pelo celular; o motor responde no navegador.")

        seen = 0
        last_engine_fen = None
        pending_engine_fen = None
        pending_engine_since = None
        last_unsynced_fen = None
        last_san_error = None
        last_status_at = time.monotonic()
        paused = False
        pause_url = None
        pause_max_moves = 0
        last_pause_status = time.monotonic()
        while True:
            if os.name == "nt" and f3_pressed() and not paused:
                paused = True
                pause_url = driver.current_url
                pause_max_moves = seen
                last_pause_status = time.monotonic()
                print("F3: motor pausado. Aguardando a próxima partida...", flush=True)

            try:
                elements = driver.find_elements(
                    By.CSS_SELECTOR, ".move-list .node, .move-list-row .node"
                )
                texts = [element.text for element in elements]
            except (StaleElementReferenceException, WebDriverException):
                time.sleep(0.5)
                continue

            moves = []
            for text in texts:
                san = text.strip().replace("−", "-")
                san = re.sub(r"^\d+\.(?:\.\.)?\s*", "", san).strip()
                if MOVE_RE.fullmatch(san):
                    moves.append(san)

            if len(moves) < seen:
                seen = 0
                last_engine_fen = None
                pending_engine_fen = None
                pending_engine_since = None

            live_board = read_live_board(driver)
            board = chess.Board()
            uci_moves = []
            positions = []
            parse_failed = False
            try:
                for san in moves:
                    move = board.parse_san(san)
                    uci_moves.append(move.uci())
                    board.push(move)
                    positions.append(board.fen())
            except ValueError as exc:
                parse_failed = True
                if str(exc) != last_san_error:
                    print(f"Lista de lances temporariamente ilegível: {exc}", flush=True)
                    last_san_error = str(exc)
                if live_board is None:
                    time.sleep(POLL_INTERVAL)
                    continue
                board = live_board
                if board.fen() != last_unsynced_fen:
                    print("Usando a posição atual do tabuleiro para decidir o lance.", flush=True)
                    last_unsynced_fen = board.fen()
            else:
                last_san_error = None

            if live_board and live_board.fen() != board.fen():
                board = live_board
                if board.fen() != last_unsynced_fen:
                    print("Posição nova lida diretamente do tabuleiro.", flush=True)
                    last_unsynced_fen = board.fen()
            elif live_board:
                last_unsynced_fen = None

            if paused:
                pause_max_moves = max(pause_max_moves, len(moves))
                new_game = (
                    pause_max_moves > 0
                    and len(moves) < pause_max_moves
                    and board.ply() <= 6
                ) or (
                    driver.current_url != pause_url
                    and len(moves) <= 2
                    and live_board is not None
                )
                if new_game:
                    print("Próxima partida detectada.", flush=True)
                    engine_turn, engine_color = ask_engine_color()
                    paused = False
                    seen = 0
                    last_engine_fen = None
                    pending_engine_fen = None
                    pending_engine_since = None
                    last_unsynced_fen = None
                    print("Nova partida detectada; motor retomado.", flush=True)
                else:
                    if time.monotonic() - last_pause_status >= STATUS_INTERVAL:
                        print(
                            "Pausado; aguardando a próxima partida. "
                            "Pressione F3 para pausar.",
                            flush=True,
                        )
                        last_pause_status = time.monotonic()
                    seen = len(moves)
                    time.sleep(POLL_INTERVAL)
                    continue

            if pending_engine_fen is not None:
                if board.fen() != pending_engine_fen:
                    last_engine_fen = pending_engine_fen
                    print("Lance do motor confirmado pelo tabuleiro.", flush=True)
                    pending_engine_fen = None
                    pending_engine_since = None
                elif time.monotonic() - pending_engine_since >= 4:
                    print(
                        "O tabuleiro não confirmou o lance; vou tentar executá-lo novamente.",
                        flush=True,
                    )
                    pending_engine_fen = None
                    pending_engine_since = None

            for ply, uci in enumerate(uci_moves[seen:], start=seen):
                side = "white" if ply % 2 == 0 else "black"
                if side != engine_color:
                    fen = positions[ply]
                    print(f"Oponente: {uci}\nFEN: {fen}", flush=True)
                    try:
                        driver.execute_script(
                            "window.__chessPositionFen = arguments[0];"
                            "window.dispatchEvent(new CustomEvent('chess-position',"
                            "{detail: arguments[0]}));",
                            fen,
                        )
                    except (JavascriptException, WebDriverException):
                        pass

            if (
                board.turn == engine_turn
                and board.fen() != last_engine_fen
                and pending_engine_fen is None
                and board.legal_moves
            ):
                try:
                    engine_move = play_engine_move(board.copy())
                    if engine_move:
                        pending_engine_fen = board.fen()
                        pending_engine_since = time.monotonic()
                        print(f"Motor: {engine_move.uci()}", flush=True)
                        time.sleep(ENGINE_MOVE_DELAY)
                        click_square(driver, engine_move.from_square, engine_turn)
                        time.sleep(SQUARE_CLICK_GAP)
                        click_square(driver, engine_move.to_square, engine_turn)
                        if engine_move.promotion:
                            choose_promotion_piece(
                                driver,
                                chess.piece_symbol(engine_move.promotion),
                                engine_turn,
                            )
                        time.sleep(BOARD_UPDATE_WAIT)
                except (
                    chess.engine.EngineError,
                    OSError,
                    NoSuchElementException,
                    TimeoutException,
                    WebDriverException,
                ) as exc:
                    print(f"Erro ao calcular ou clicar o lance do motor: {exc}")
            elif (
                board.turn != engine_turn
                and pending_engine_fen is None
                and time.monotonic() - last_status_at >= STATUS_INTERVAL
            ):
                print("Aguardando o lance do oponente; monitoramento ativo.", flush=True)
                last_status_at = time.monotonic()

            seen = len(uci_moves) if parse_failed else len(moves)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("Encerrando...")
    except WebDriverException as exc:
        print(f"Erro ao iniciar/controlar o Chrome: {exc}")
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()

