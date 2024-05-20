import sqlite3
import simpy
import numpy as np
from itertools import permutations
from multiprocessing import Pool, cpu_count
from baseball import Hitter, Diamond
import time
import os
import tempfile
import shutil


# 데이터베이스 연결 및 테이블 생성
def init_db(db_path):
    # 디렉토리가 존재하지 않으면 생성
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inning_log (
            game_id INTEGER,
            inning INTEGER,
            at_bat_number INTEGER,
            batter TEXT,
            event TEXT,
            score INTEGER
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


def save_inning_log_to_db(db_path, log_entries):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany(
        'INSERT INTO inning_log (game_id, inning, at_bat_number, batter, event, score) VALUES (?, ?, ?, ?, ?, ?)',
        log_entries)
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


def at_bat(env, diamond, lineup, current_batter_index, inning, at_bat_number, game_id, inning_log):
    hitter = lineup[current_batter_index]
    result = simulate_at_bat(hitter)

    # 먼저 base_on_balls와 hit_by_pitch를 처리해야, 확률 계산이 올바르게 됨
    if result == 'base_on_balls' or result == 'hit_by_pitch':
        diamond.base_on_balls(hitter)
        inning_log.append((game_id, inning, at_bat_number, hitter.name, result, diamond.score))
        return
    else:
        if result == 'hit':
            diamond.hit(hitter)
        elif result == 'double':
            diamond.double(hitter)
        elif result == 'triple':
            diamond.triple(hitter)
        elif result == 'home_run':
            diamond.home_run(hitter)
        else:
            diamond.out()

    inning_log.append((game_id, inning, at_bat_number, hitter.name, result, diamond.score))
    yield env.timeout(1)


def simulate_inning(env, lineup, inning_scores, game_id, inning_log):
    diamond = Diamond()
    current_batter_index = 0
    inning = 1
    at_bat_number = 1

    while diamond.outs < 3:
        yield env.process(at_bat(env, diamond, lineup, current_batter_index, inning, at_bat_number, game_id, inning_log))
        current_batter_index = (current_batter_index + 1) % len(lineup)
        at_bat_number += 1
        yield env.timeout(0.1)

    inning_scores.append(diamond.score)


def simulate_game(lineup, game_id, inning_log):
    inning_scores = []
    env = simpy.Environment()
    for inning in range(1, 541): # 9 이닝 * 60 경기
        env.process(simulate_inning(env, lineup, inning_scores, game_id, inning_log))
        env.run()
    avg_score = np.mean(inning_scores) * 9
    return avg_score


def simulate_lineup(args):
    lineup_order, temp_dir, game_id_start = args
    start_time = time.time()
    inning_log = []
    avg_score = simulate_game(lineup_order, game_id_start, inning_log)
    lineup_str = ', '.join([player.name for player in lineup_order])

    temp_file_path = os.path.join(temp_dir, f"{lineup_str.replace(', ', '_')}.txt")
    with open(temp_file_path, 'w') as f:
        f.write(f"lineup,average_score\n")
        f.write(f"{lineup_str},{avg_score}\n")

    inning_log_file_path = os.path.join(temp_dir, f"{lineup_str.replace(', ', '_')}_log.txt")
    with open(inning_log_file_path, 'w') as f:
        f.write(f"game_id,inning,at_bat_number,batter,event,score\n")
        for log_entry in inning_log:
            f.write(','.join(map(str, log_entry)) + '\n')

    end_time = time.time()
    return (lineup_str, avg_score, end_time - start_time)


def find_optimal_lineup(players, temp_dir):
    permutations_list = list(permutations(players))
    total_permutations = len(permutations_list)
    game_id_start = 1

    with Pool(processes=cpu_count()) as pool:
        results = []
        start_time = time.time()

        futures = [pool.apply_async(simulate_lineup, [(lineup, temp_dir, game_id_start + i * 144)]) for i, lineup in
                   enumerate(permutations_list)]
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
        if temp_file.endswith('_log.txt'):
            inning_log_entries = []
            with open(temp_file_path, 'r') as f:
                next(f)  # Skip header
                for line in f:
                    inning_log_entries.append(tuple(line.strip().split(',')))
            save_inning_log_to_db(db_path, inning_log_entries)
        elif temp_file.endswith('.txt'):
            with open(temp_file_path, 'r') as f:
                next(f)  # Skip header
                for line in f:
                    lineup, avg_score = line.strip().rsplit(',', 1)
                    save_result_to_db(db_path, lineup, float(avg_score))


# 선수 데이터
# players_data = [
#     Hitter("호세 페르난데스", plate_appearance=600, at_bat=550, hit=170, double=25, triple=1, home_run=14, bb=45, hbp=5, pace=0.2),
#     Hitter("양의지", plate_appearance=520, at_bat=470, hit=153, double=30, triple=1, home_run=18, bb=40, hbp=3, pace=0.2),
#     Hitter("양석환", plate_appearance=540, at_bat=490, hit=130, double=20, triple=0, home_run=25, bb=40, hbp=2, pace=0.1),
#     Hitter("김재환", plate_appearance=580, at_bat=520, hit=140, double=25, triple=1, home_run=27, bb=55, hbp=4, pace=0.1),
#     Hitter("허경민", plate_appearance=530, at_bat=480, hit=135, double=18, triple=2, home_run=9, bb=35, hbp=4, pace=0.2),
#     Hitter("정수빈", plate_appearance=610, at_bat=560, hit=150, double=20, triple=4, home_run=5, bb=50, hbp=6, pace=0.4),
#     Hitter("김인태", plate_appearance=450, at_bat=400, hit=105, double=10, triple=0, home_run=8, bb=28, hbp=3, pace=0.2),
#     Hitter("강승호", plate_appearance=490, at_bat=440, hit=110, double=22, triple=1, home_run=19, bb=30, hbp=2, pace=0.3),
#     Hitter("박계범", plate_appearance=380, at_bat=340, hit=85, double=12, triple=1, home_run=5, bb=20, hbp=2, pace=0.1)
# ]

players_data = [
    Hitter("구자욱" , plate_appearance=201, at_bat=178, hit=53, double=11, triple=1, home_run=8, bb=15, hp=6, pace=0.3),
    Hitter("김헌곤" , plate_appearance=98, at_bat=88, hit=28, double=4, triple=0, home_run=4, bb=8, hp=1, pace=0.2),
    Hitter("맥키넌" , plate_appearance=183, at_bat=151, hit=53, double=7, triple=1, home_run=4, bb=29, hp=0, pace=0.1),
    Hitter("김영웅" , plate_appearance=194, at_bat=170, hit=51, double=8, triple=1, home_run=11, bb=21, hp=2, pace=0.3),
    Hitter("류지혁" , plate_appearance=98, at_bat=83, hit=25, double=2, triple=1, home_run=1, bb=12, hp=1, pace=0.3),
    Hitter("이재현" , plate_appearance=121, at_bat=112, hit=31, double=8, triple=1, home_run=4, bb=14, hp=0, pace=0.2),
    Hitter("강민호" , plate_appearance=144, at_bat=130, hit=34, double=2, triple=0, home_run=2, bb=12, hp=2, pace=0.1),
    Hitter("오재일" , plate_appearance=57, at_bat=51, hit=11, double=4, triple=1, home_run=2, bb=6, hp=0, pace=0.1),
    Hitter("이성규" , plate_appearance=102, at_bat=80, hit=19, double=4, triple=0, home_run=7, bb=11, hp=6, pace=0.3),
]
# 데이터베이스 경로 설정
db_path = '../database/simulation_results.db'

# 데이터베이스 초기화
conn = init_db(db_path)
conn.close()

# 임시 파일 디렉토리 생성
temp_dir = tempfile.mkdtemp()

# 최적의 타순 찾기
best_lineup, best_score = find_optimal_lineup(players_data, temp_dir)
print("최적의 타순:", best_lineup)
print("평균 득점:", best_score)

# 임시 파일에서 결과 병합
merge_results_from_temp_files(temp_dir, db_path)

# 임시 파일 삭제
shutil.rmtree(temp_dir)

# 데이터베이스 결과 확인
def print_results(db_path, limit=10):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Print results table
        print("Results Table:")
        cursor.execute(f'SELECT * FROM results LIMIT {limit}')
        results = cursor.fetchall()
        for row in results:
            print(row)

        # Print game_log table
        print("\nInning Log Table:")
        cursor.execute(f'SELECT * FROM inning_log LIMIT {limit}')
        game_log = cursor.fetchall()
        for row in game_log:
            print(row)

        conn.close()
    except sqlite3.OperationalError as e:
        print(f"OperationalError: {e}")

# 데이터베이스 경로 설정
db_path = '../database/simulation_results.db'

# 데이터베이스 내용 출력
print_results(db_path, limit=10)
