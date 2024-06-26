import numpy as np

class Hitter:
    def __init__(self, name, plate_appearance, at_bat, hit, double, triple, home_run, bb, hbp, pace):
        self.name = name
        self.plate_appearance = plate_appearance
        self.at_bat = at_bat
        self.hit = hit
        self.double = double
        self.triple = triple
        self.home_run = home_run
        self.bb = bb
        self.hbp = hbp
        self.pace = pace  # 주력에 따라 한 베이스를 더 뛸 수 있는 능력

    def single_prob(self):
        return (self.hit - self.double - self.triple - self.home_run) / self.at_bat

    def double_prob(self):
        return self.double / self.at_bat

    def triple_prob(self):
        return self.triple / self.at_bat

    def home_run_prob(self):
        return self.home_run / self.at_bat

    def bb_prob(self):
        return self.bb / self.plate_appearance

    def hbp_prob(self):
        return self.hbp / self.plate_appearance

    def runner_run_when_hit(self):
        return np.random.rand() < self.pace

class Diamond:
    def __init__(self):
        self.base = [None, None, None]  # 1루, 2루, 3루
        self.outs = 0
        self.score = 0

    def clear_base(self):
        self.base = [None, None, None]

    def hit(self, hitter):
        runners = [hitter] + self.base
        self.base = [None, None, None]

        for i in range(3, -1, -1):  # 3루 주자부터 1루 주자 순으로 처리
            if runners[i] is not None:
                if i == 3:
                    self.score += 1  # 3루 주자가 홈으로 들어옴
                else:
                    next_base = i + 1 if not runners[i].runner_run_when_hit() else i + 2
                    if next_base < 3:
                        self.base[next_base] = runners[i]
                    else:
                        self.score += 1  # 주자가 홈으로 들어옴

    def double(self, hitter):
        runners = [None, hitter] + self.base
        self.base = [None, None, None]

        for i in range(3, -1, -1):
            if runners[i] is not None:
                if i >= 2:
                    self.score += 1  # 2루 이상 주자가 홈으로 들어옴
                else:
                    next_base = i + 2 if not runners[i].runner_run_when_hit() else i + 3
                    if next_base < 3:
                        self.base[next_base] = runners[i]
                    else:
                        self.score += 1  # 주자가 홈으로 들어옴

    def triple(self, hitter):
        runners = [None, None, hitter] + self.base
        self.base = [None, None, None]

        for i in range(3, -1, -1):
            if runners[i] is not None:
                if i >= 1:
                    self.score += 1  # 1루 이상 주자가 홈으로 들어옴
                else:
                    next_base = i + 3
                    if next_base < 3:
                        self.base[next_base] = runners[i]
                    else:
                        self.score += 1  # 주자가 홈으로 들어옴

    def home_run(self, hitter):
        self.score += 1  # 타자가 홈으로 들어옴
        for runner in self.base:
            if runner is not None:
                self.score += 1  # 모든 주자가 홈으로 들어옴
        self.base = [None, None, None]  # 베이스 비우기

    def base_on_balls(self, hitter):
        if self.base[0] is None:
            self.base[0] = hitter
        elif self.base[1] is None:
            self.base[1] = self.base[0]
            self.base[0] = hitter
        elif self.base[2] is None:
            self.base[2] = self.base[1]
            self.base[1] = self.base[0]
            self.base[0] = hitter
        else:
            self.score += 1  # 주자가 홈으로 들어옴
            self.base = [hitter, self.base[0], self.base[1]]  # 기존 주자들 이동

    def hit_by_pitch(self, hitter):
        self.base_on_balls(hitter)

    def out(self):
        self.outs += 1
        if self.outs % 3 == 0:
            self.clear_base()

    def double_play(self):
        # Double play is possible if there are less than 2 outs
        if self.outs % 3 < 2:
            if self.base[0] is not None:  # There is a runner on 1st base
                if self.base[1] is not None:  # There is also a runner on 2nd base
                    self.outs += 2  # Two outs are made
                    self.base[1] = None
                    self.base[0] = None
                else:  # Only runner on 1st base
                    self.outs += 2  # Two outs are made
                    self.base[0] = None
                # Check if inning ends
                if self.outs % 3 == 0:
                    self.clear_base()