from math import sqrt
import numpy as np
import os
import sys

from snakebattleclient.internals.Element import Element
from snakebattleclient.internals.Point import Point
from snakebattleclient.internals.SnakeAction import SnakeAction


class Board:
    """ Class describes the Board field for Bomberman game."""

    def __init__(self, board_string):
        self._string = board_string.replace('\n', '')
        self._len = len(self._string)  # the length of the string
        self._size = int(sqrt(self._len))  # size of the board

    def get_point_by_shift(self, shift):
        return Point(shift % self._size, shift / self._size)

    def find_first_element(self, *element_types):
        _result = []
        for i in range(self._size * self._size):
            point = self.get_point_by_shift(i)
            for type in element_types:
                if self.has_element_at(point, type):
                    return point
        return None

    def get_my_head(self):
        return self.find_first_element(Element('HEAD_DEAD'), 
                                        Element('HEAD_DOWN'), Element('HEAD_UP'),
                                       Element('HEAD_LEFT'), Element('HEAD_RIGHT'), Element('HEAD_EVIL'),
                                       Element('HEAD_FLY'), Element('HEAD_SLEEP'))

    def _find_all(self, *element_types):
        """ Returns the list of points for the given element type."""
        _points = []
        for i in range(self._size * self._size):
            point = self.get_point_by_shift(i)
            for type in element_types:
                if self.has_element_at(point, type):
                    _points.append(point)
        return _points

    def get_walls(self):
        return self._find_all(Element('WALL'))

    def get_stones(self):
        return self._find_all(Element('STONE'))

    def get_barriers(self):
        """ Return the list of barriers Points."""
        points = set()
        points.update(self._find_all(Element('WALL'), Element('START_FLOOR'), Element('ENEMY_HEAD_SLEEP'),
                                     Element('ENEMY_TAIL_INACTIVE'), Element('TAIL_INACTIVE'), Element('STONE')))
        return list(points)

    def is_barrier_at(self, point):
        return self.get_barriers().__contains__(point)

    def get_apples(self):
        return self._find_all(Element('APPLE'))

    def am_i_evil(self):
        return self._find_all(Element('HEAD_EVIL')).__contains__(self.get_my_head())

    def am_i_flying(self):
        return self._find_all(Element('HEAD_FLY')).__contains__(self.get_my_head())

    def get_flying_pills(self):
        return self._find_all(Element('FLYING_PILL'))

    def get_furry_pills(self):
        return self._find_all(Element('FURY_PILLS'))

    def get_gold(self):
        return self._find_all(Element('GOLD'))

    def get_start_points(self):
        return self._find_all(Element('START_FLOOR'))

    def get_element_at(self, point):
        """ Return an Element object at coordinates x,y."""
        return Element(self._string[self._xy2strpos(point.get_x(), point.get_y())])

    def has_element_at(self, point, element_object):
        if point.is_out_of_board(self._size):
            return False
        return element_object == self.get_element_at(point)

    def find_element(self, type):
        for i in range(self._size * self._size):
            point = self.get_point_by_shift(i)
            if self.has_element_at(point, type):
                return point
        return None

    def get_shift_by_point(self, point):
        return point.get_y() * self._size + point.get_x()

    def _strpos2pt(self, strpos):
        return Point(*self._strpos2xy(strpos))

    def _strpos2xy(self, strpos):
        return (strpos % self._size, strpos // self._size)

    def _xy2strpos(self, x, y):
        return self._size * y + x

    def print_board(self):
        print(self._line_by_line())

    def _line_by_line(self):
        return '\n'.join([self._string[i:i + self._size]
                          for i in range(0, self._len, self._size)])

    def to_string(self):
        return ("Board:\n{brd}".format(brd=self._line_by_line()))
        
    def assign(self, index, c:Element):
        self._string = self._string[:index] + c.get_char() + self._string[index+1:]
        
    def assign_point(self, p: Point, c:Element):
        self.assign(self._xy2strpos(p.get_x(),p.get_y()), c)
        
    def get_access_repr(self, head, rage, stones=False, body=False):
        try:
            access_board = np.ones((self._size, self._size), dtype=int) * 666
            #print(access_board.tolist())
            
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
            
            if rage:
                good_els = good_elements + enemies + [Element('STONE')]
            else:
                if not stones and not body:
                    good_els = base_good_elements
                elif body and not stones:
                    good_els = good_elements
                else:
                    good_els = good_elements + [Element('STONE')]
            
            #head = self.get_my_head()
            if head is None:
                return None
            sources = set()
            sources.add(head)
            dist = 0
            steps = 0
            while len(sources) > 0 and steps < 25:
                steps += 1
                new_sources = set()
                for p in sources:
                    access_board[p.get_x(),p.get_y()] = dist
                    next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                    for st in next_steps:
                        if st.is_out_of_board(self._size):
                            continue
                        if access_board[st.get_x(),st.get_y()] != 666:
                            continue
                        if self.get_element_at(st) in good_els and st not in new_sources:
                            new_sources.add(st)
                dist += 1
                sources = new_sources
                
            if steps == 1000:
                print('AAAAA', sources)
                #print(len(sources), dist)
                #print(access_board.tolist())
            #print(access_board.tolist())
            return access_board
        except Exception as e:
            print('Exception get_access_repr', e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            
    def create_access_reprs(self, head):
        self.access_board = self.get_access_repr(head, rage=False)
        #self.access_board_body_stones = self.get_access_repr(head, rage=False, stones=True, body=True)
        #self.access_board_body = self.get_access_repr(head, rage=False, stones=False, body=True)
        self.access_board_rage = self.get_access_repr(head, rage=True)
        
    def get_dist_to(self, p, rage, body=False, stones=False):
        if rage:
            if not body:
                return self.access_board_rage[p.get_x(),p.get_y()]
            else:
                return self.access_board_body[p.get_x(),p.get_y()]
        else:
            if not body and not stones:
                return self.access_board[p.get_x(),p.get_y()]
            elif body and not stones:
                return self.access_board_body[p.get_x(),p.get_y()]
            else:
                return self.access_board_body_stones[p.get_x(),p.get_y()]
        
    def get_next_step_to(self, p, rage):
        access_board = self.access_board_rage if rage else self.access_board
        d = self.get_dist_to(p, rage)
        sources = set()
        sources.add(p)
        while d != 1:
            d -= 1
            new_sources = set()
            for p in sources:
                next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                for st in next_steps:
                    if st.is_out_of_board(self._size):
                        continue
                    if access_board[st.get_x(),st.get_y()] == d and st not in new_sources:
                        new_sources.add(st)       
            sources = new_sources
        return sources         
        
    def update_board(self, head_in, rage, old_dir: SnakeAction):
        #print('update_board')
        if True:
            head = self.get_my_head()
            if head is None:
                if head_in is None:
                    return
                head = head_in
            
            my_tails = [
                Element('TAIL_END_DOWN'),
                Element('TAIL_END_LEFT'),
                Element('TAIL_END_UP'),
                Element('TAIL_END_RIGHT'),
                Element('TAIL_INACTIVE'),
            ]
            
            enemies = [
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
            
            enemies_head = [
                Element('ENEMY_HEAD_DOWN'),
                Element('ENEMY_HEAD_LEFT'),
                Element('ENEMY_HEAD_RIGHT'),
                Element('ENEMY_HEAD_UP'),
            ]
            
            tail = self.find_first_element(*my_tails)
            if tail is not None:
                index = self._xy2strpos(tail.get_x(), tail.get_y())
                self.assign(index, Element('NONE'))
            
            if rage and False:
                index = self._xy2strpos(head.get_x(), head.get_y())
                if old_dir == SnakeAction.DOWN:
                    self.assign(index, Element('HEAD_DOWN'))
                if old_dir == SnakeAction.UP:
                    self.assign(index, Element('HEAD_UP'))
                if old_dir == SnakeAction.LEFT:
                    self.assign(index, Element('HEAD_LEFT'))
                if old_dir == SnakeAction.RIGHT:
                    self.assign(index, Element('HEAD_RIGHT'))
                    
            #print('before first')
                    
            trans = True
            count = 0
            while trans and count < 100 and False:
                count +=1
                trans = False
                for i in range(1,self._size-1):
                    for k in range(1,self._size-1):
                        p = Point(i,k)
                        a = self.get_element_at(p)
                        if a == Element('WALL'):
                            continue
                        next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                        bad_els = [Element('WALL')]
                        s = np.count_nonzero([self.get_element_at(x) in bad_els for x in next_steps])
                        #print(s)
                        if s >= 3:
                            trans = True
                            #print(s)
                            index = self._xy2strpos(i, k)
                            self.assign(index, Element('WALL'))
                            
            #print('before second')
                            
            if not rage:       
                trans = True
                count = 0
                while trans and count < 100 and False:
                    count +=1
                    trans = False
                    for i in range(1,self._size-1):
                        for k in range(1,self._size-1):
                            p = Point(i,k)
                            a = self.get_element_at(p)
                            if a == Element('WALL'):
                                continue
                            next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                            bad_els = [Element('WALL')] + enemies
                            s = np.count_nonzero([self.get_element_at(x) in bad_els for x in next_steps])
                            if s >= 3:
                                trans = True
                                index = self._xy2strpos(i, k)
                                self.assign(index, Element('WALL'))
                                
            #print('before third')     
                                
            if not rage:       
                trans = True
                count = 0
                while trans and count < 100 and False:
                    count +=1
                    trans = False
                    for i in range(1,self._size-1):
                        for k in range(1,self._size-1):
                            p = Point(i,k)
                            a = self.get_element_at(p)
                            if a == Element('WALL'):
                                continue
                            next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                            bad_els = [Element('WALL'), Element('STONE')] + enemies
                            s = np.count_nonzero([self.get_element_at(x) in bad_els for x in next_steps])
                            if s >= 3:
                                trans = True
                                index = self._xy2strpos(i, k)
                                self.assign(index, Element('STONE'))
                    
            #print('before fourth')
            if False:
                for i in range(1,self._size-1):
                    for k in range(1,self._size-1):
                        p = Point(i,k)
                        a = self.get_element_at(p)
                        if a != Element('ENEMY_HEAD_EVIL'):
                            continue
                        next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                        for p2 in next_steps:
                            index = self._xy2strpos(p2.get_x(), p2.get_y())
                            if self.get_element_at(p2) in enemies:
                                self.assign(index, Element('ENEMY_HEAD_EVIL'))
                            else:
                                self.assign(index, Element('WALL'))
            
            if False:            
                trans = True
                count = 0
                while trans and count < 100:
                    count +=1
                    trans = False
                    for i in range(1,self._size-1):
                        for k in range(1,self._size-1):
                            p = Point(i,k)
                            a = self.get_element_at(p)
                            if a != Element('ENEMY_HEAD_EVIL'):
                                continue
                            next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                            for p2 in next_steps:
                                index = self._xy2strpos(p2.get_x(), p2.get_y())
                                if self.get_element_at(p2) in enemies:
                                    self.assign(index, Element('ENEMY_HEAD_EVIL'))
                                    trans = True
                        
            #print('before fifth', rage)       
            if not rage:
                #print('TESTST')
                for i in range(1,self._size-1):
                    for k in range(1,self._size-1):
                        p = Point(i,k)
                        a = self.get_element_at(p)
                        if a not in enemies_head:
                            continue
                        next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                        for p2 in next_steps:
                            index = self._xy2strpos(p2.get_x(), p2.get_y())
                            self.assign(index, Element('WALL'))
                            #print('CHECK ENEMIES HEAD')
                            
            
                   
            # for i in range(1,self._size-1):
                # for k in range(1,self._size-1):
                    # p = Point(i,k)
                    # a = self.get_element_at(p)
                    # if a == Element('WALL'):
                        # continue
                    # next_steps = [p.shift_top(1), p.shift_bottom(1), p.shift_left(1), p.shift_right(1)]
                    
                    # if rage:
                        # bad_els = [Element('WALL')]
                    # else:
                        # bad_els = [Element('WALL'), Element('STONE'), ] + enemies
                    
                    # s = np.count_nonzero([self.get_element_at(x) in bad_els for x in next_steps])
                    # #print(s)
                    # if s >= 3:
                        # #print(s)
                        # index = self._xy2strpos(i, k)
                        # self.assign(index, Element('WALL'))                
        # except Exception as e:
            # print('Exception', e)
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            # print(exc_type, fname, exc_tb.tb_lineno)


if __name__ == '__main__':
    raise RuntimeError("This module is not designed to be ran from CLI")
