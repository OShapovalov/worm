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

from collections import defaultdict

actions = list(SnakeAction)

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    level=logging.ERROR)

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

enemies_bodies = [
    Element('ENEMY_HEAD_DOWN'),
    Element('ENEMY_HEAD_LEFT'),
    Element('ENEMY_HEAD_RIGHT'),
    Element('ENEMY_HEAD_UP'),
    Element('ENEMY_BODY_HORIZONTAL'),
    Element('ENEMY_BODY_VERTICAL'),
    Element('ENEMY_BODY_LEFT_DOWN'),
    Element('ENEMY_BODY_LEFT_UP'),
    Element('ENEMY_BODY_RIGHT_DOWN'),
    Element('ENEMY_BODY_RIGHT_UP'),
]

enemies_tails = [
    Element('ENEMY_TAIL_END_DOWN'),
    Element('ENEMY_TAIL_END_LEFT'),
    Element('ENEMY_TAIL_END_UP'),
    Element('ENEMY_TAIL_END_RIGHT'),
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
        if a not in base_good_elements+[Element('STONE')]+enemies_bodies+enemies_tails:
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
        target_els = [Element('APPLE'), Element('FURY_PILL'), Element('GOLD'), Element('STONE')] + enemies_bodies
    
    if gcb.get_element_at(new_point) in target_els:    
        score += value
        
    if gcb.get_element_at(new_point) == Element('FURY_PILL'):
        score += 35*value
        return score
        
    if gcb.get_element_at(new_point) in enemies_bodies:
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
                if gcb.get_element_at(new_point) in enemies_bodies:
                    score += 55*value
                #TODO:
                next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                if not rage:
                    s = np.count_nonzero([gcb.get_element_at(x) in good_elements for x in next_steps])
                else:
                    s = np.count_nonzero([gcb.get_element_at(x) in good_elements+[Element('STONE'),]+enemies_bodies+enemies_tails for x in next_steps])
                if s > 1:
                    score += value
                    #return score
        value /= 8
    return score


scores = defaultdict(lambda: 1000,
                     {
                        Element('APPLE').get_char():1,
                        Element('FURY_PILL').get_char():10000,
                        Element('GOLD').get_char():10,
                        Element('STONE').get_char():3,
                     })

class Logic:
    def __init__(self, n):
        self.tick = 0
        self.n = n
        self.df = pd.DataFrame()
        self.prev_action = SnakeAction.RIGHT
        self.prev_rage = False
        self.ticks_rage = 0
        self.head = None
        
    def __call__(self, gcb: Board):
        try:
            board_str = gcb._line_by_line()
            src_gcb = Board(board_str)
        
            my_head = gcb.get_my_head()
          
            if my_head is None:
                print('my_head is None')
                if self.head is None:
                    return SnakeAction.RIGHT
                if self.prev_action == SnakeAction.RIGHT:
                    self.head = self.head.shift_right(1)
                if self.prev_action == SnakeAction.LEFT:
                    self.head = self.head.shift_left(1)
                if self.prev_action == SnakeAction.UP:
                    self.head = self.head.shift_top(1)
                if self.prev_action == SnakeAction.DOWN:
                    self.head = self.head.shift_bottom(1)
                my_head = self.head
                #return SnakeAction.RIGHT
            else:
                self.head = my_head
                
            my_head_el = gcb.get_element_at(my_head)
            rage = my_head_el == Element('HEAD_EVIL')
            
            if rage:
                if self.prev_action == SnakeAction.RIGHT:
                    my_head_el = Element('HEAD_RIGHT')
                if self.prev_action == SnakeAction.LEFT:
                    my_head_el = Element('HEAD_LEFT')
                if self.prev_action == SnakeAction.UP:
                    my_head_el = Element('HEAD_UP')
                if self.prev_action == SnakeAction.DOWN:
                    my_head_el = Element('HEAD_DOWN')
                
            #print(my_head, my_head_el)
            gcb.assign_point(my_head, my_head_el)
            
            first_rage = False
            
            if rage and not self.prev_rage:
                first_rage = True
                self.ticks_rage = 9
            self.ticks_rage -= 1
            self.prev_rage = rage
            if self.ticks_rage <= 0:
                rage = False
                
            use_new = True#not rage
            
            #gcb.update_board(my_head, rage, self.prev_action)
            gcb.update_board(my_head, False, self.prev_action)
            if use_new:
                gcb.create_access_reprs(my_head)
            #my_head_el = gcb.get_element_at(my_head)
            
            if my_head_el not in good_positions and False:
                self.prev_action = get_same_direction(my_head_el)
                return self.prev_action
            else:
                if True:
                    if use_new:
                        if not rage:
                            targets = gcb._find_all(Element('APPLE'), Element('FURY_PILL'), Element('GOLD'))
                        else:
                            print('rage: ', len(gcb._find_all(*enemies_bodies)))
                            targets = gcb._find_all(Element('APPLE'), Element('FURY_PILL'), Element('GOLD'), Element('STONE'), *enemies_bodies)
                            
                                              #targets = [t for t in targets if src_gcb.get_element_at(t) != Element('WALL')]
                            
                        if first_rage:
                            pass
                            #print('TARGETS:', targets)
                            
                        dists = [gcb.get_dist_to(t, rage) for t in targets]
                        
                        targets_with_dists = [(t, d if gcb.get_element_at(t) != Element('FURY_PILL') else 0.66*d, scores[gcb.get_element_at(t).get_char()] ) for t,d in zip(targets, dists) if d!= 666]
                        targets_with_dists = [tdc for tdc in targets_with_dists if tdc[1]<self.ticks_rage or gcb.get_element_at(tdc[0]) in [Element('APPLE'), Element('FURY_PILL'), Element('GOLD')] ]
                        targets_with_dists.sort(key=itemgetter(1))
                        
                        for tdc in targets_with_dists:
                            if gcb.get_element_at(tdc[0]) in enemies_bodies:
                                print('ENEMY FOUND:', tdc[1])
                        
                        #targets_with_dists = targets_with_dists[:10]
                        
                        if rage:
                            pass
                            #print('targets_with_dists:', targets_with_dists)
                        
                        if len(targets_with_dists) > 0 and True:
                            dist = targets_with_dists[0][1]
                            targets_with_dists = [td for td in targets_with_dists if td[1]==dist]
                            
                            solution_found = False
                            ps = []
                            
                            for t, d, c in targets_with_dists:
                                if gcb.get_element_at(t) in enemies_bodies:
                                    ps = list(gcb.get_next_step_to(t, rage))
                                    if len(ps) > 0:
                                        solution_found = True
                                        break
                            
                            if not solution_found:
                                targets_with_dists.sort(key=itemgetter(2))
                                #if rage:
                                    #print('targets_with_dists sorted by:', targets_with_dists)
                                
                                ne = 1
                                while True and ne <= 3:
                                
                                    target = targets_with_dists[-ne]
                                    ne +=1
                                    if rage:
                                        pass
                                        #print('TARGET:', target)
                                    
                                    
                                    ps = gcb.get_next_step_to(target[0], rage)
                                    ps = list(ps)
                                    if len(ps) > 0:
                                        break
                                    #ps = [x for x in ps if src_gcb.get_element_at(x) != Element('WALL')]
                            
                            if rage:
                                pass
                                #print('ps:', ps)
                            
                            if rage:
                                pass
                                #print(ps)
                            if len(ps)>0:
                                random.shuffle(ps)
                                p = ps[0]
                                if gcb.get_element_at(p) == Element('FURY_PILL'):
                                    self.ticks_rage += 10
                                if my_head.shift_top(1) == p:
                                    self.prev_action = SnakeAction.UP
                                    return self.prev_action
                                if my_head.shift_bottom(1) == p:
                                    self.prev_action = SnakeAction.DOWN
                                    return self.prev_action
                                if my_head.shift_left(1) == p:
                                    self.prev_action = SnakeAction.LEFT
                                    return self.prev_action
                                if my_head.shift_right(1) == p:
                                    self.prev_action = SnakeAction.RIGHT
                                    return self.prev_action
                            else:
                                print('use old algo:', targets_with_dists)
                        
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
                    #print(rage, res)
                    res.sort(key=itemgetter(1))
                    #print(rage, res)
                    if len(res) == 0:
                        for action_index in range(4):
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
                            if gcb.get_element_at(new_point) != Element('WALL'):
                                res.append((action_index, get_score(gcb, new_point, rage)))
                    if len(res) == 0:
                        return
                    action_index = res[-1][0]

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
    n = 22
    while n < 2222:
        n += 1
        logic = Logic(n)

        gcb = GameClient(
            "http://codebattle-pro-2020s1.westeurope.cloudapp.azure.com/codenjoy-contest/board/player/hr6e15um5ufrmm8z2d4k?code=6440009553401168331&gameName=snakebattle")
        gcb.run(logic)


if __name__ == '__main__':
    main()
