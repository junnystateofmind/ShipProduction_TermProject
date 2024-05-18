import sqlite3
import simpy
import numpy as np
from itertools import permutations
from multiprocessing import Pool, cpu_count
from baseball import Hitter, Diamond
import time
import os
import tempfile


def init_db(db_path):
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            lineup TEXT,
            average_score REAL
        )
    ''')
    conn.commit()
    return conn


def save_result_to_db(db_path, lineup, average_score):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO results (lineup, average_score) VALUES (?, ?)', (lineup, average_score))
    conn.commit()
    conn.close()


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

    yield env.timeout(1)


def game(env, lineup, game_scores):
    diamond = Diamond()
    current_batter_index = 0
    while diamond.outs < 27:
        yield env.process(at_bat(env, diamond, lineup, current_batter_index))
        current_batter_index = (current_batter_index + 1) % len(lineup)
        yield env.timeout(0.1)

    game_scores.append(diamond.score)


def simulate_season(lineup):
    game_scores = []
    env = simpy.Environment()
    env.process(simulate_season_process(env, lineup, num_games=144, game_scores=game_scores))
    env.run()
    avg_score = np.mean(game_scores)
    return avg_score


def simulate_season_process(env, lineup, num_games, game_scores):
    for _ in range(num_games):
        yield env.process(game(env, lineup, game_scores))


def simulate_lineup(args):
    lineup_order, temp_dir = args
    start_time = time.time()
    avg_score = simulate_season(lineup_order)
    lineup_str = ', '.join([player.name for player in lineup_order])

    temp_file_path = os.path.join(temp_dir, f"{lineup_str.replace(', ', '_')}.txt")
    with open(temp_file_path, 'w') as f:
        f.write(f"{lineup_str},{avg_score}\n")

    end_time = time.time()
    return (lineup_str, avg_score, end_time - start_time)


def find_optimal_lineup(players, temp_dir):
    permutations_list = list(permutations(players))
    total_permutations = len(permutations_list)

    with Pool(processes=cpu_count()) as pool:
        results = []
        start_time = time.time()

        futures = [pool.apply_async(simulate_lineup, [(lineup, temp_dir)]) for lineup in permutations_list]
        for i, future in enumerate(futures):
            result = future.get()
            results.append(result)
            lineup_str, avg_score, elapsed_time = result

            progress = (i + 1) / total_permutations
            elapsed_total_time = time.time() - start_time
            estimated_total_time = elapsed_total_time / progress
            remaining_time = estimated_total_time - elapsed_total_time

            print(
                f"Completed {i + 1}/{total_permutations} ({progress:.2%}) - Lineup: {lineup_str}, Avg Score: {avg_score}, Time Taken: {elapsed_time:.2f} seconds")
            print(f"Estimated time remaining: {remaining_time:.2f} seconds")

        best_lineup = None
        best_score = 0

        for lineup_str, avg_score, _ in results:
            if avg_score > best_score:
                best_score = avg_score
                best_lineup = lineup_str

    return best_lineup, best_score


def merge_results_from_temp_files(temp_dir, db_path):
    for temp_file in os.listdir(temp_dir):
        temp_file_path = os.path.join(temp_dir, temp_file)
        with open(temp_file_path, 'r') as f:
            for line in f:
                lineup, avg_score = line.strip().split(',')
                save_result_to_db(db_path, lineup, float(avg_score))


# 선수 데이터
players_data = [
    Hitter("Ohtani Shohei", plate_appearance=639, at_bat=537, hit=138, double=26, triple=8, home_run=34, bb=96, hbp=5,
           pace=0.6),
    Hitter("Mike Trout", plate_appearance=507, at_bat=438, hit=123, double=24, triple=1, home_run=40, bb=90, hbp=4,
           pace=0.5),
    Hitter("Anthony Rendon", plate_appearance=248, at_bat=200, hit=49, double=10, triple=0, home_run=6, bb=23, hbp=1,
           pace=0.4),
    Hitter("Albert Pujols", plate_appearance=296, at_bat=267, hit=65, double=11, triple=0, home_run=12, bb=14, hbp=5,
           pace=0.2),
    Hitter("Justin Upton", plate_appearance=362, at_bat=274, hit=63, double=12, triple=0, home_run=17, bb=39, hbp=10,
           pace=0.3),
    Hitter("Jared Walsh", plate_appearance=454, at_bat=385, hit=98, double=27, triple=2, home_run=15, bb=45, hbp=4,
           pace=0.3),
    Hitter("David Fletcher", plate_appearance=665, at_bat=603, hit=157, double=26, triple=3, home_run=2, bb=28, hbp=3,
           pace=0.5),
    Hitter("Max Stassi", plate_appearance=319, at_bat=272, hit=61, double=13, triple=1, home_run=13, bb=38, hbp=7,
           pace=0.3),
    Hitter("Taylor Ward", plate_appearance=375, at_bat=324, hit=81, double=19, triple=0, home_run=8, bb=38, hbp=7,
           pace=0.4)
]

# 데이터베이스 경로 설정
db_path = '../database/simulation_results.db'
temp_dir = tempfile.mkdtemp()

# 데이터베이스 초기화
conn = init_db(db_path)
conn.close()

# 최적의 타순 찾기
best_lineup, best_score = find_optimal_lineup(players_data, temp_dir)
merge_results_from_temp_files(temp_dir, db_path)
print("최적의 타순:", best_lineup)
print("평균 득점:", best_score)

# 임시 파일 삭제
import shutil

shutil.rmtree(temp_dir)
