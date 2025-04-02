import time
import uuid
from concurrent import futures
from typing import Iterable, Optional
import sys

import grpc

import tic_tac_toe_pb2_grpc as ttt_grpc
import tic_tac_toe_pb2 as ttt

def get_winner(moves: Iterable[ttt.Move]) -> Optional[int]:
    winning_combinations = (
        (1, 2, 3), (4, 5, 6), (7, 8, 9),  # Rows
        (1, 4, 7), (2, 5, 8), (3, 6, 9),  # Cols
        (1, 5, 9), (3, 5, 7),             # Diagonals
    )

    x_moves = []
    o_moves = []

    for move in moves:
        if move.mark == ttt.MARK_CROSS:
            x_moves.append(move.cell)
        elif move.mark == ttt.MARK_NOUGHT:
            o_moves.append(move.cell)

    for combination in winning_combinations:
        if all(cell in x_moves for cell in combination):
            return ttt.MARK_CROSS
        if all(cell in o_moves for cell in combination):
            return ttt.MARK_NOUGHT

    return None

class TicTacToeServicer(ttt_grpc.TicTacToeServicer):
    def __init__(self):
        self.games = {}

    def CreateGame(self, request, context):
        game_id = uuid.uuid4().int % (2**30)
        game = ttt.Game(id=game_id, is_finished=False, moves=[])
        self.games[game_id] = game
        print("CreateGame()")
        return game

    def GetGame(self, request, context):
        game_id = request.game_id
        if game_id not in self.games:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('Game not found')
            return ttt.Game()
        print(f"GetGame(game_id={game_id})")
        return self.games[game_id]

    def MakeMove(self, request, context):
        game_id = request.game_id
        if game_id not in self.games:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('Game not found')
            return ttt.Game()

        game = self.games[game_id]
        if game.is_finished:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details('Game is already finished')
            return game

        move = request.move
        if move.cell < 1 or move.cell > 9:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Invalid cell number')
            return game

        if move.mark != game.turn:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details('Not your turn')
            return game

        for existing_move in game.moves:
            if existing_move.cell == move.cell:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details('Cell is already occupied')
                return game

        print(f'MakeMove(game_id={game_id}, move=Move(mark={move.mark}, cell={move.cell})')
        game.moves.append(move)
        winner = get_winner(game.moves)

        if len(game.moves) == 9:
            game.is_finished = True
            return game

        if winner is None:
            game.turn = ttt.MARK_CROSS if game.turn == ttt.MARK_NOUGHT else ttt.MARK_NOUGHT
            return game
        else:
            game.is_finished = True
            game.winner = winner
            return game




if __name__ == "__main__":
    # Hardcoded port number
    port = 50051  # Change this to your desired port
    host = "0.0.0.0"  # Listen on all interfaces

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ttt_grpc.add_TicTacToeServicer_to_server(TicTacToeServicer(), server)
    server.add_insecure_port(f'{host}:{port}')
    server.start()
    print(f"Server listening on {host}:{port}")

    try:
        while True:
            time.sleep(1)
    except grpc.RpcError as e:
        print(f"gRPC error - {e}")
    except KeyboardInterrupt:
        server.stop(0)
        exit(0)
    
