import sqlite3
import simpy
import numpy as np
from itertools import permutations
from baseball import Hitter, Diamond

# 데이터베이스 연결 및 테이블 생성
def init_db():
    conn = sqlite3.connect('simulation_results.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            lineup TEXT,
            average_score REAL
        )
    ''')
    conn.commit()
    return conn

def save_result_to_db(conn, lineup, average_score):
    cursor = conn.cursor()
    cursor.execute('INSERT INTO results (lineup, average_score) VALUES (?, ?)', (lineup, average_score))
    conn.commit()

def simulate_at_bat(hitter):
    result = np.random.rand()
    if result < hitter.single_prob():
        return 'hit'
    elif result < hitter.single_prob() + hitter.double_prob():
        return 'double'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob():
        return 'triple'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob() + hitter.home_run_prob():
        return 'home_run'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob() + hitter.home_run_prob() + hitter.bb_prob():
        return 'base_on_balls'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob() + hitter.home_run_prob() + hitter.bb_prob() + hitter.hbp_prob():
        return 'hit_by_pitch'
    else:
        return 'out'

def at_bat(env, diamond, lineup, current_batter_index):
    hitter = lineup[current_batter_index]
    result = simulate_at_bat(hitter)

    if result == 'hit':
        diamond.hit(hitter)
    elif result == 'double':
        diamond.double(hitter)
    elif result == 'triple':
        diamond.triple(hitter)
    elif result == 'home_run':
        diamond.home_run(hitter)
    elif result == 'base_on_balls':
        diamond.base_on_balls(hitter)
    elif result == 'hit_by_pitch':
        diamond.hit_by_pitch(hitter)
    else:
        diamond.out()

    print(f"Time: {env.now}, Batter: {hitter.name}, Result: {result}, Outs: {diamond.outs}, Score: {diamond.score}")

    yield env.timeout(1)  # 각 타석 간의 간격을 시뮬레이션 (여기서는 단순히 1로 설정)

def game(env, lineup, game_scores):
    diamond = Diamond()
    current_batter_index = 0
    while diamond.outs < 27:
        yield env.process(at_bat(env, diamond, lineup, current_batter_index))
        current_batter_index = (current_batter_index + 1) % len(lineup)
        yield env.timeout(0.1)  # 각 타석 간의 시간 간격 (여기서는 0.1로 설정)

    print(f"Game completed. Total Score: {diamond.score}")
    game_scores.append(diamond.score)

def simulate_season(env, lineup, num_games, game_scores):
    for _ in range(num_games):
        yield env.process(game(env, lineup, game_scores))

def find_optimal_lineup(players, conn):
    best_lineup = None
    best_score = 0

    for lineup_order in permutations(players):
        game_scores = []
        env = simpy.Environment()
        env.process(simulate_season(env, lineup_order, num_games=162, game_scores=game_scores))
        env.run()

        avg_score = np.mean(game_scores)
        if avg_score > best_score:
            best_score = avg_score
            best_lineup = lineup_order

        lineup_str = ', '.join([player.name for player in lineup_order])
        print(f"Lineup: {lineup_str}, Avg Score: {avg_score}")
        save_result_to_db(conn, lineup_str, avg_score)

    return best_lineup, best_score

# 선수 데이터
players_data = [
    Hitter("Ohtani Shohei", plate_appearance=639, at_bat=537, hit=138, double=26, triple=8, home_run=34, bb=96, hbp=5, pace=0.6),
    Hitter("Mike Trout", plate_appearance=507, at_bat=438, hit=123, double=24, triple=1, home_run=40, bb=90, hbp=4, pace=0.5),
    Hitter("Anthony Rendon", plate_appearance=248, at_bat=200, hit=49, double=10, triple=0, home_run=6, bb=23, hbp=1, pace=0.4),
    Hitter("Albert Pujols", plate_appearance=296, at_bat=267, hit=65, double=11, triple=0, home_run=12, bb=14, hbp=5, pace=0.2),
    Hitter("Justin Upton", plate_appearance=362, at_bat=274, hit=63, double=12, triple=0, home_run=17, bb=39, hbp=10, pace=0.3),
    Hitter("Jared Walsh", plate_appearance=454, at_bat=385, hit=98, double=27, triple=2, home_run=15, bb=45, hbp=4, pace=0.3),
    Hitter("David Fletcher", plate_appearance=665, at_bat=603, hit=157, double=26, triple=3, home_run=2, bb=28, hbp=3, pace=0.5),
    Hitter("Max Stassi", plate_appearance=319, at_bat=272, hit=61, double=13, triple=1, home_run=13, bb=38, hbp=7, pace=0.3),
    Hitter("Taylor Ward", plate_appearance=375, at_bat=324, hit=81, double=19, triple=0, home_run=8, bb=38, hbp=7, pace=0.4)
]

# 데이터베이스 초기화
conn = init_db()

# 최적의 타순 찾기
best_lineup, best_score = find_optimal_lineup(players_data, conn)
print("최적의 타순:", [player.name for player in best_lineup])
print("평균 득점:", best_score)

# 데이터베이스 연결 종료
conn.close()
