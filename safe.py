from snakebattleclient.SnakeBattleClient import GameClient
import random
import logging

from snakebattleclient.internals.SnakeAction import SnakeAction
from snakebattleclient.internals.Board import Board
from snakebattleclient.internals.Point import Point
from snakebattleclient.internals.Element import Element

import pandas as pd
import numpy as np
from operator import itemgetter
import os
import sys

actions = list(SnakeAction)

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    level=logging.INFO)

my_down = Element('HEAD_DOWN')
my_left = Element('HEAD_LEFT')
my_right = Element('HEAD_RIGHT')
my_up = Element('HEAD_UP')

good_positions = [my_down, my_left, my_right, my_up]

base_good_elements = [
    Element('NONE'),
    Element('APPLE'),
    Element('FLYING_PILL'),
    Element('FURY_PILL'),
    Element('GOLD'),
                ]

good_elements = [
    Element('NONE'),
    Element('APPLE'),
    Element('FLYING_PILL'),
    Element('FURY_PILL'),
    Element('GOLD'),
    Element('TAIL_END_DOWN'),
    Element('TAIL_END_LEFT'),
    Element('TAIL_END_UP'),
    Element('TAIL_END_RIGHT'),
    Element('TAIL_INACTIVE'),
    Element('BODY_HORIZONTAL'),
    Element('BODY_VERTICAL'),
    Element('BODY_LEFT_DOWN'),
    Element('BODY_LEFT_UP'),
    Element('BODY_RIGHT_DOWN'),
    Element('BODY_RIGHT_UP'),
                ]

enemies = [
    Element('ENEMY_HEAD_DOWN'),
    Element('ENEMY_HEAD_LEFT'),
    Element('ENEMY_HEAD_RIGHT'),
    Element('ENEMY_HEAD_UP'),
    Element('ENEMY_TAIL_END_DOWN'),
    Element('ENEMY_TAIL_END_LEFT'),
    Element('ENEMY_TAIL_END_UP'),
    Element('ENEMY_TAIL_END_RIGHT'),
    Element('ENEMY_BODY_HORIZONTAL'),
    Element('ENEMY_BODY_VERTICAL'),
    Element('ENEMY_BODY_LEFT_DOWN'),
    Element('ENEMY_BODY_LEFT_UP'),
    Element('ENEMY_BODY_RIGHT_DOWN'),
    Element('ENEMY_BODY_RIGHT_UP'),
]


def get_same_direction(my_head):
    action = None
    if my_head == my_down:
        action = SnakeAction.DOWN
    elif my_head == my_up:
        action = SnakeAction.UP
    elif my_head == my_left:
        action = SnakeAction.LEFT
    elif my_head == my_right:
        action = SnakeAction.RIGHT
    if action is None:
        action = SnakeAction.RIGHT 
    return action

def is_opposite(a:SnakeAction, b:Element):
    #print(str(a), b.get_char())
    if a == SnakeAction.DOWN and b == my_up:
        return True
    if a == SnakeAction.UP and b == my_down:
        return True
    if a == SnakeAction.LEFT and b == my_right:
        return True
    if a == SnakeAction.RIGHT and b == my_left:
        return True
    return False

def is_good(gcb: Board, p: Point, rage, allow_stones, allow_body=False):
    a = gcb.get_element_at(p)
    #print('NEW EL:', a.get_char())
    if not rage: 
        if not allow_stones and not allow_body and a not in base_good_elements:
            return False
        if allow_stones and not allow_body and a not in base_good_elements+[Element('STONE')]:
            return False
        if allow_stones and allow_body and a not in base_good_elements+[Element('STONE')]+good_elements:
            return False
    else:
        if a not in base_good_elements+[Element('STONE')]+enemies:
            return False
    next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
    if not rage:
        if not allow_stones:
            s = np.count_nonzero([gcb.get_element_at(x) in good_elements for x in next_steps])
        else:
            s = np.count_nonzero([gcb.get_element_at(x) in good_elements+[Element('STONE')] for x in next_steps])
    else:
        s = np.count_nonzero([gcb.get_element_at(x) in good_elements+[Element('STONE')] for x in next_steps])
    #print('s:', s)
    return s > 0
    
def get_score(gcb, new_point, rage):
    n = 25
    score = 0
    value = 8 ** (n+1)
    
    if not rage:
        target_els = [Element('APPLE'), Element('FURY_PILL'), Element('GOLD')]
    else:
        target_els = [Element('APPLE'), Element('FURY_PILL'), Element('GOLD'), Element('STONE')] + enemies
    
    if gcb.get_element_at(new_point) in target_els:    
        score += value
        
    if gcb.get_element_at(new_point) == Element('FURY_PILL'):
        score += 35*value
        return score
        
    if gcb.get_element_at(new_point) in enemies:
        score += 75*value
        return score
    
    value /= 8
        
    for d in range(1, n):
        p1 = new_point.shift_top(d)
        p2 = new_point.shift_bottom(d)
        p3 = new_point.shift_right(d)
        p4 = new_point.shift_left(d)
        ps = [p1, p2, p3, p4]
        for p in ps:
            if p.is_out_of_board(gcb._size):
                continue
            if gcb.get_element_at(p) in target_els:
                #score += value
                if gcb.get_element_at(p) == Element('FURY_PILL'):
                    score += 35*value
                if gcb.get_element_at(new_point) in enemies:
                    score += 55*value
                #TODO:
                next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                if not rage:
                    s = np.count_nonzero([gcb.get_element_at(x) in good_elements for x in next_steps])
                else:
                    s = np.count_nonzero([gcb.get_element_at(x) in good_elements+[Element('STONE'),]+enemies for x in next_steps])
                if s > 1:
                    score += value
                    #return score
        value /= 8
    return score


class Logic:
    def __init__(self, n):
        self.tick = 0
        self.n = n
        self.df = pd.DataFrame()
        self.prev_action = SnakeAction.RIGHT
        self.prev_rage = False
        self.ticks_rage = 0
        
    def __call__(self, gcb: Board):
        try:
            board_str = gcb._line_by_line()
        
            my_head = gcb.get_my_head()
            if my_head is None:
                return SnakeAction.RIGHT
            my_head_el = gcb.get_element_at(my_head)
            rage = my_head_el == Element('HEAD_EVIL')
            if rage and not self.prev_rage:
                self.ticks_rage = 9
            self.ticks_rage -= 1
            self.prev_rage = rage
            if self.ticks_rage <= 0:
                rage = False
            
            gcb.update_board(rage, self.prev_action)
            my_head_el = gcb.get_element_at(my_head)
            
            if my_head_el not in good_positions:
                self.prev_action = get_same_direction(my_head_el)
                return self.prev_action
            else:
                i = 0
                while i < 1000:
                    # if not rage:
                        # targets = gcb._find_all(Element('APPLE'), Element('FURY_PILL'), Element('GOLD'))
                    # else:
                        # targets = gcb._find_all(Element('APPLE'), Element('FURY_PILL'), Element('GOLD'), Element('STONE'))
                    res = []
                    for action_index in range(4):
                        #action_index = random.randint(0,3)
                        act = actions[action_index]
                        if is_opposite(act, my_head_el):
                            continue
                        if act == SnakeAction.UP:
                            new_point = my_head.shift_top(1)
                        elif act == SnakeAction.DOWN:
                            new_point = my_head.shift_bottom(1)
                        elif act == SnakeAction.LEFT:
                            new_point = my_head.shift_left(1)
                        elif act == SnakeAction.RIGHT:
                            new_point = my_head.shift_right(1)
                        if is_good(gcb, new_point, rage, False):
                            #print('GOOD:', act, 'RAGE:', rage)
                            res.append((action_index, get_score(gcb, new_point, rage)))
                            
                    if len(res) == 0:
                        for action_index in range(4):
                            #action_index = random.randint(0,3)
                            act = actions[action_index]
                            if is_opposite(act, my_head_el):
                                continue
                            if act == SnakeAction.UP:
                                new_point = my_head.shift_top(1)
                            elif act == SnakeAction.DOWN:
                                new_point = my_head.shift_bottom(1)
                            elif act == SnakeAction.LEFT:
                                new_point = my_head.shift_left(1)
                            elif act == SnakeAction.RIGHT:
                                new_point = my_head.shift_right(1)
                            if is_good(gcb, new_point, rage, True):
                                #print('GOOD:', act, 'RAGE:', rage)
                                res.append((action_index, get_score(gcb, new_point, rage)))
                                
                    if len(res) == 0:
                        for action_index in range(4):
                            #action_index = random.randint(0,3)
                            act = actions[action_index]
                            if is_opposite(act, my_head_el):
                                continue
                            if act == SnakeAction.UP:
                                new_point = my_head.shift_top(1)
                            elif act == SnakeAction.DOWN:
                                new_point = my_head.shift_bottom(1)
                            elif act == SnakeAction.LEFT:
                                new_point = my_head.shift_left(1)
                            elif act == SnakeAction.RIGHT:
                                new_point = my_head.shift_right(1)
                            if is_good(gcb, new_point, rage, True, True):
                                #print('GOOD:', act, 'RAGE:', rage)
                                res.append((action_index, get_score(gcb, new_point, rage)))
                            
                    random.shuffle(res)
                    print(rage, res)
                    res.sort(key=itemgetter(1))
                    print(rage, res)
                    if len(res) == 0:
                        return SnakeAction.RIGHT
                    action_index = res[-1][0]
                    #self.prev_action = res[-1][0]
                    break
                    i += 1
                if i == 1000:
                    self.prev_action = SnakeAction.RIGHT
                    return self.prev_action
                self.df = self.df.append({'tick':self.tick, 'board':board_str, 'action':action_index}, ignore_index=True)
                self.df.to_csv(f'logs/log_new_{self.n}.csv',index=False)
                self.tick += 1
                self.prev_action = actions[action_index]
                return self.prev_action
        except Exception as e:
            print('Exception', e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            pass
            
    def get_df(self):
        return self.df


def main():
    print('STARTTTT')
    n = 1000
    while n < 1e9:
        n += 1
        logic = Logic(n)
        try:
            gcb = GameClient(
                "http://codebattle-pro-2020s1.westeurope.cloudapp.azure.com/codenjoy-contest/board/player/3b9ochln0rtk51i3t7i7?code=3213556217336188020&gameName=snakebattle")
            gcb.run(logic)
        except (KeyboardInterrupt, SystemExit):
            exit(-1)
            raise
        except Exception as e:
            exit(-1)
            #logic.get_df().to_csv(f'logs/logn_{n}.csv',index=False)
            pass

if __name__ == '__main__':
    main()




