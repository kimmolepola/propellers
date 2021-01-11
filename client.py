import pygame
import time
import socket
from random import randint
import glob
import os
import math

dir_path = os.path.dirname(os.path.realpath(__file__))

with open (dir_path+"/files/server_host_and_port_for_client.txt") as f:
    lines = f.readlines()
    server_host = lines[0][:-1]
    server_port = int(lines[1])

if server_host == "localhost":
    server_host = socket.gethostname()

clock = pygame.time.Clock()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
own_port = randint(1025, 65535)
sock.bind((socket.gethostname(), own_port))

other_players_dic = {}
other_players_list = []
destroyed_list = []


print("loading background")
try:
    background_list = [None for i in glob.glob(dir_path+'/files/background/*.JPG')]
    for fullfilename in glob.glob(dir_path+'/files/background/*.JPG'):
    
        base = os.path.basename(fullfilename)
        filename = os.path.splitext(base)[0]
        
        background_list[int(filename)-1] = pygame.image.load(fullfilename)
        
except Exception:
    print("error: background filenames have to be consecutive numbers starting from one")
    quit()

background_tiles_horizontal_amount = int(math.sqrt(len(background_list)))
background_tile_width = background_list[0].get_width()
background_tile_height = background_list[0].get_height()

player_sprite = pygame.image.load(dir_path+"/files/sprites/player.png")
other_player_sprite = pygame.image.load(dir_path+"/files/sprites/player2.png")
destroyed_sprite = pygame.image.load(dir_path+"/files/sprites/destroyed.png")
bullet_sprite = pygame.image.load(dir_path+"/files/sprites/bullet.png")

bullets_list = []

map_width = background_tiles_horizontal_amount * background_tile_width
map_height = len(background_list)/background_tiles_horizontal_amount*background_tile_height

pygame.init()
info_object = pygame.display.Info()
width, height = int(info_object.current_w/3*2), int(info_object.current_h/3*2)
pygame.key.set_repeat(50, 100)

view_offset = [0, 0]
distance = 3
bullet_distance = 65

world_x_max = 131071
world_x_min = -131072

pygame.mixer.init()
crash_sound = pygame.mixer.Sound(dir_path+"/files/sounds/crash.wav")
shoot_sound = pygame.mixer.Sound(dir_path+"/files/sounds/shoot.wav")
propeller_sound = pygame.mixer.Sound(dir_path+"/files/sounds/propeller_2.wav")
gun_load_sound = pygame.mixer.Sound(dir_path+"/files/sounds/gun_load.wav")
pygame.mixer.music.load(dir_path+"/files/sounds/propeller.wav")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)
music = pygame.mixer.Sound(dir_path+"/files/music/spy_hunter.wav")
pygame.mixer.Sound.play(music, loops = -1)
        
class main():
    
    def __init__(self, sock, bullets_list):
        
        self.sock = sock
        self.server_host = server_host
        self.server_port = server_port

        self.player_id = -1
        self.in_previous_sequence_number = -1

        print("client waiting for server")
        while self.player_id == -1:
            self.acquire_player_id()
        
        
        shot = pygame.image.load(dir_path+"/files/sprites/bullet.png")
        
        self.player_sprite_upper_left = (width / 2 - player_sprite.get_width() / 2, height / 2 - player_sprite.get_height() / 2)

        self.time_now = 0

        self.direction_time = 0
        self.direction = 180
        
        self.shoot_amount = 0
        self.shoot_time = 0

        self.position = [0, 0]
        self.destroyed = False
        self.sprite = player_sprite
        
        self.out_sequence_number = 0
        
        self.bullets_list = bullets_list
        
        print("client up")
        screen = pygame.display.set_mode((width, height)) 

        self.main_loop(screen, width, height, shot)

    def in_sequence_number_is_ok(self, in_sequence_number):
        in_sequence_number_range = 31
        margin = 8
        limit1 = self.in_previous_sequence_number + margin
        if limit1 <= in_sequence_number_range:  # if sequence number range doesn't overflow
            if in_sequence_number > self.in_previous_sequence_number and in_sequence_number <= limit1:
                self.in_previous_sequence_number = in_sequence_number
                return True
            return False        
        limit2 = limit1 - in_sequence_number_range - 1  # if sequence number range overflows
        if (in_sequence_number > self.in_previous_sequence_number and in_sequence_number <= limit1) or (in_sequence_number > -1 and in_sequence_number <= limit2):
            self.in_previous_sequence_number = in_sequence_number
            return True
        return False
    
    def check_socket(self):
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) == 3:
                self.process_instant_data(data)
            if len(data) >= 8:
                self.process_periodic_data(data)
            if len(data) == 4:
                self.process_destroy_data(data)
        except socket.error:
            pass
    
    def process_destroy_data(self, data):
        last_byte_of_data = data[-1:]
        in_sequence_number = int.from_bytes(last_byte_of_data, 'big')
        if self.in_sequence_number_is_ok(in_sequence_number):
            p_id = int.from_bytes(data[:2], 'big')
            if p_id == self.player_id:
                self.destroyed = True
                self.sprite = destroyed_sprite
                pygame.mixer.Sound.play(crash_sound)
                pygame.mixer.music.stop()
            else:
                if p_id not in other_players_dic:
                    other_players_dic[p_id] = Other_player(p_id)
                    other_players_list.append(other_players_dic[p_id])
                other_players_dic[p_id].destroyed = True
                other_players_dic[p_id].sprite = destroyed_sprite
                destroyed_list.append(other_players_dic[p_id])
                pygame.mixer.Sound.play(crash_sound)
    
    def process_periodic_data(self, data):
        last_byte_of_data = data[-1:]
        in_sequence_number = int.from_bytes(last_byte_of_data, 'big')
        if self.in_sequence_number_is_ok(in_sequence_number):
            index = 0
            while index + 6 < len(data) - 1:
                p_id = int.from_bytes(data[index:index + 2], 'big')
                p_pos_and_dst_and_dir = int.from_bytes(data[index + 2:index + 7], 'big')
                index += 7
                p_pos_x = p_pos_and_dst_and_dir >> 22
                p_pos_x -= world_x_max + 1
                p_pos_y = p_pos_and_dst_and_dir >> 4
                p_pos_y = p_pos_y & 262143  # bitwise and, mask first 18 bits
                p_pos_y -= world_x_max + 1
                p_dst = p_pos_and_dst_and_dir >> 2
                p_dst = p_dst & 1  # bitwise and, mask first bit
                p_dir = p_pos_and_dst_and_dir & 3  # bitwise and, mask first 2 bits
                if p_id == self.player_id:
                    self.position[0] = p_pos_x
                    self.position[1] = p_pos_y
                    if p_dst == 1 and not self.destroyed:
                        self.destroyed = True
                        self.sprite = destroyed_sprite
                else:
                    if p_id not in other_players_dic:
                        other_players_dic[p_id] = Other_player(p_id)
                        other_players_list.append(other_players_dic[p_id])
                    other_players_dic[p_id].x = p_pos_x
                    other_players_dic[p_id].y = p_pos_y
                    if p_dst == 1 and not other_players_dic[p_id].destroyed:
                        other_players_dic[p_id].destroyed = True
                        other_players_dic[p_id].sprite = destroyed_sprite
                    other_players_dic[p_id].direction = self.convert_digit_to_direction(p_dir)

    def convert_digit_to_direction(self, digit):
        if digit == 0:
            return 0
        if digit == 1:
            return 90
        if digit == 2:
            return 180
        if digit == 3:
            return 270
        
    def convert_direction_to_digit(self, direction):
        if direction == 0:
            return 0
        if direction == 90:
            return 1
        if direction == 180:
            return 2
        if direction == 270:
            return 3
                                
    def process_instant_data(self, data):
        last_byte_of_data = data[-1:]
        last_byte_of_data = int.from_bytes(last_byte_of_data, 'big')
        in_sequence_number = last_byte_of_data >> 3  # shift right by 3 bits
        if self.in_sequence_number_is_ok(in_sequence_number):
            other_player_action = last_byte_of_data & 7  # bitwise and, mask 00000111
            other_player_shoot = other_player_action >> 2
            other_player_direction = other_player_action & 3
            other_player_id = int.from_bytes(data[:-1], 'big')
            if other_player_id != self.player_id:
                if other_player_id not in other_players_dic:
                    other_players_dic[other_player_id] = Other_player(other_player_id)
                    other_players_list.append(other_players_dic[other_player_id])
                other_players_dic[other_player_id].direction = self.convert_digit_to_direction(other_player_direction)
                if other_player_shoot == 1:
                    other_players_dic[other_player_id].shoot_amount = 6
                    pygame.mixer.Sound.play(shoot_sound)

    
    def acquire_player_id(self):
        data = 0
        data = data.to_bytes(2, 'big')
        self.sock.sendto(data, (self.server_host, self.server_port))
        time.sleep(1)
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) == 5:
                if self.player_id == -1:
                    self.player_id = int.from_bytes(data[2:4], 'big')
                    print("id " + str(self.player_id))
                    self.in_previous_sequence_number = int.from_bytes(data[4:], 'big')-1
        except socket.error:
            pass
    
    def main_loop(self, screen, width, height, shot):

        while 1:
            clock.tick(30)
            self.time_now = time.time()
            if (self.shoot_amount > 0):
                self.shoot_amount -= 1
                self.bullets_list.append(bullet(-1, self.position[0], self.position[1], self.direction))
                
            self.check_socket()
            self.do_updates(screen, shot, width, height)
            self.check_events()        


    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit(0)
                
            if not self.destroyed:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_j and self.time_now > self.direction_time + 0.15:
                        if (self.direction == 270):
                            self.direction = 0
                        else:
                            self.direction += 90
                        self.direction_time = self.time_now
                        self.send_data(0)
                        pygame.mixer.Sound.play(propeller_sound)
                    elif event.key == pygame.K_l and self.time_now > self.direction_time + 0.15:
                        if self.direction == 0:
                            self.direction = 270
                        else: 
                            self.direction -= 90
                        self.direction_time = self.time_now
                        self.send_data(0)
                        pygame.mixer.Sound.play(propeller_sound)
                    elif event.key == pygame.K_f:
                        if self.time_now > self.shoot_time + 2:
                            pygame.mixer.Sound.play(shoot_sound)
                            self.shoot_time = self.time_now
                            self.shoot_amount = 6
                            self.send_data(1)
                        else:
                            pygame.mixer.Sound.play(gun_load_sound)
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        exit(0)
                        

    def send_data(self, shoot):
        if self.direction == 0:
            direc = 0
        elif self.direction == 90:
            direc = 1
        elif self.direction == 180:
            direc = 2
        else:
            direc = 3
        action = shoot << 2 | direc
        data = self.out_sequence_number << 3 | action
        data = data.to_bytes(1, 'big')
        self.sock.sendto(data, (self.server_host, self.server_port))
        self.sock.sendto(data, (self.server_host, self.server_port))
        self.sock.sendto(data, (self.server_host, self.server_port))
        
        self.out_sequence_number += 1
        self.out_sequence_number = self.out_sequence_number % 32
                
    def do_updates(self, screen, shot, width, height):
        screen.fill(0)
        if not self.destroyed:
            if self.direction == 0:
                self.position[1] += distance
            elif self.direction == 90:
                self.position[0] += distance
            elif self.direction == 180:
                self.position[1] -= distance
            elif self.direction == 270:
                self.position[0] -= distance
            
        view_offset[0] = -self.position[0]
        view_offset[1] = -self.position[1]
        
        horizontal_tile_counter = 0
        vertical_tile_counter = 0
        for tile in background_list:
            screen.blit(tile, (horizontal_tile_counter*background_tile_width+view_offset[0]-map_width/2, vertical_tile_counter*background_tile_height+view_offset[1]-map_height/2))
            
            horizontal_tile_counter += 1
            if horizontal_tile_counter > background_tiles_horizontal_amount-1:
                horizontal_tile_counter = 0
                vertical_tile_counter += 1
            
        for op in destroyed_list:
            op_sprite_2 = pygame.transform.rotate(op.sprite, op.direction)
            screen.blit(op_sprite_2, (op.x - op_sprite_2.get_width() / 2 + width / 2 + view_offset[0], op.y - op_sprite_2.get_height() / 2 + height / 2 + view_offset[1]))

        player_sprite_2 = pygame.transform.rotate(self.sprite, self.direction)
        screen.blit(player_sprite_2, (self.player_sprite_upper_left))
        
        for op in other_players_list:
            if not op.destroyed:
                op.move()
                if op.shoot_amount > 0:
                    op.shoot_amount -= 1
                    bullets_list.append(bullet(op.player_id, op.x, op.y, op.direction))
                op_sprite_2 = pygame.transform.rotate(op.sprite, op.direction)
                screen.blit(op_sprite_2, (op.x - op_sprite_2.get_width() / 2 + width / 2 + view_offset[0], op.y - op_sprite_2.get_height() / 2 + height / 2 + view_offset[1]))
        
        for b in self.bullets_list:
            if b.time > 0:
                screen.blit(bullet_sprite, (b.x - bullet_sprite.get_width() / 2 + width / 2 + view_offset[0], b.y - bullet_sprite.get_height() / 2 + height / 2 + view_offset[1]))
                b.move()
                b.time -= 1
            
        if len(self.bullets_list) > 300:
            new_list = []
            for b in self.bullets_list:
                if b.time > 0:
                    new_list.append(b)
            self.bullets_list = new_list

        pygame.display.flip()


class Other_player():

    def __init__(self, player_id):
        self.player_id = player_id
        self.x = 0
        self.y = 0
        self.direction = 0
        self.shoot_amount = 0
        self.destroyed = False
        self.sprite = other_player_sprite
        
    def move(self):
        if (self.direction == 0):
            self.y += distance
        elif (self.direction == 90):
            self.x += distance
        elif (self.direction == 180):
            self.y -= distance
        elif (self.direction == 270):
            self.x -= distance


class bullet():
    
    def __init__(self, player_id, x, y, direction):
        self.player_id = player_id
        self.direction = direction
        self.time = 20
        self.x = x
        self.y = y
        if (self.direction == 0):
            self.y += player_sprite.get_height()
        elif (self.direction == 90):
            self.x += player_sprite.get_height()
        elif (self.direction == 180):
            self.y -= player_sprite.get_height()
        elif (self.direction == 270):
            self.x -= player_sprite.get_height()
        
    def move(self):
        if (self.direction == 0):
            self.y += bullet_distance
        elif (self.direction == 90):
            self.x += bullet_distance
        elif (self.direction == 180):
            self.y -= bullet_distance
        elif (self.direction == 270):
            self.x -= bullet_distance        
        
main(sock, bullets_list)

