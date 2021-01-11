import socket
import time
import pygame
import os

dir_path = os.path.dirname(os.path.realpath(__file__))

with open (dir_path+"/files/server_port_for_server.txt") as f:
    server_port = int(f.read())

print(server_port)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
sock.bind((socket.gethostname(), server_port))


clock = pygame.time.Clock()

players_dic = {}
players_list = []
sequence_number_dic = {}

player_sprite = pygame.image.load(dir_path+"/files/sprites/player.png")
bullet_sprite = pygame.image.load(dir_path+"/files/sprites/bullet.png")


bullets_list = []

distance = 3
bullet_distance = 65

world_x_max = 131071
world_x_min = -131072

class main():
    def __init__(self):
        

        
        self.next_id = 0
        self.out_sequence_number = -1

        print("server up")

        periodic_data_time = time.time()

        
        while True:
            clock.tick(30)
            time_now = time.time()
            self.check_socket()
            self.move_bullets()
            self.move_players_and_shoot()
            self.check_for_collisions()
            if time_now > periodic_data_time + 3:
                periodic_data_time = time_now
                if players_list:
                    self.send_periodic_data()

    def move_bullets(self):
        for b in bullets_list:
            if b.time > 0:
                b.move()
                b.time -= 1
            
        if len(bullets_list) > 300:
            new_list = []
            for b in self.bullets_list:
                if b.time > 0:
                    new_list.append(b)
            self.bullets_list = new_list


    def new_out_sequence_number(self):
        self.out_sequence_number += 1
        if self.out_sequence_number>31:
            self.out_sequence_number = 0
        return self.out_sequence_number

    def check_for_collisions(self):
        for p in players_list:
            if p.destroyed:
                continue
            p.collision_checked = True
            for p2 in players_list:
                if p != p2 and not p2.collision_checked and not p2.destroyed:
                    if p.playerrect.colliderect(p2.playerrect):
                        print("Destroy " + str(p.player_id) + " and " + str(p2.player_id))
                        p.destroyed = True
                        p2.destroyed = True
                        
                        self.send_destroy_data(p.player_id)
                        self.send_destroy_data(p2.player_id)
            for b in bullets_list:
                if b.time > 0:
                    if p.playerrect.colliderect(b.bullet_rect):
                        print("Destroy " + str(p.player_id))
                        p.destroyed = True
                        self.send_destroy_data(p.player_id)
                    
        for p in players_list:
            p.collision_checked = False
        

    def move_players_and_shoot(self):
        for p in players_list:
            if not p.destroyed:
                p.move()
                if p.shoot_amount > 0:
                    p.shoot_amount -= 1
                    bullets_list.append(bullet(p.player_id, p.x, p.y, p.direction))
                    

    def check_socket(self):
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) == 2:
                self.create_new_player(addr)
            if len(data) == 1:
                data = int.from_bytes(data, 'big')
                in_sequence_number = data >> 3  # shift right by 3 bits
                if self.in_sequence_number_is_ok(addr, in_sequence_number):
                    action = data & 7  # bitwise and, mask 00000111
                    shoot = action >> 2
                    direction = action & 3                        
                    if addr in players_dic:
                        players_dic[addr].direction = self.convert_digit_to_direction(direction)
                        if shoot == 1:
                            players_dic[addr].shoot_amount = 6
                        self.send_instant_data(players_dic[addr], action)
                    
        except socket.error:
            pass

    def send_destroy_data(self, player_id):
        out_sequence_number = self.new_out_sequence_number()
        data = player_id.to_bytes(2, 'big')
        data2 = out_sequence_number.to_bytes(2, 'big') #sequence number fits to one byte but here payload size 4 bytes on purpose
        for p in players_list:
            sock.sendto(data+data2, p.addr)
            sock.sendto(data+data2, p.addr)
            sock.sendto(data+data2, p.addr)

    def create_new_player(self, addr):
        data = b''
        if addr not in players_dic:
            players_dic[addr] = player(addr, self.next_id)
            players_list.append(players_dic[addr])
            data = self.next_id.to_bytes(2, 'big')
            self.next_id += 1
        else:
            data = players_dic[addr].player_id.to_bytes(2, 'big')
        data2 = b''
        if self.out_sequence_number < 0:
            data2 = int(0).to_bytes(1, 'big')
        else:
            data2 = self.out_sequence_number.to_bytes(1, 'big')
        data3 = int(0).to_bytes(2, 'big')
        sock.sendto(data3+data+data2, addr)

    def in_sequence_number_is_ok(self, addr, in_sequence_number):
        in_sequence_number_range = 31
        margin = 8
        in_previous_sequence_number = -1
        if addr in sequence_number_dic:
            in_previous_sequence_number = sequence_number_dic[addr]
        limit1 = in_previous_sequence_number + margin
        if limit1<=in_sequence_number_range: #if sequence number range doesn't overflow
            if in_sequence_number > in_previous_sequence_number and in_sequence_number <= limit1:
                sequence_number_dic[addr] = in_sequence_number
                return True
            return False        
        limit2 = limit1 - in_sequence_number_range - 1 #if sequence number range overflows
        if (in_sequence_number > in_previous_sequence_number and in_sequence_number <= limit1) or (in_sequence_number > -1 and in_sequence_number <= limit2):
            sequence_number_dic[addr] = in_sequence_number
            return True
        return False
    
    def send_instant_data(self, acting_player, action):
        out_sequence_number = self.new_out_sequence_number()
        data1 = acting_player.player_id.to_bytes(2, 'big')
        sequence_number_and_action = out_sequence_number << 3 | action
        data2 = sequence_number_and_action.to_bytes(1, 'big')

        for p in players_list:
            sock.sendto(data1+data2, p.addr)
            sock.sendto(data1+data2, p.addr)
            sock.sendto(data1+data2, p.addr)

    def send_periodic_data(self):
        out_sequence_number = self.new_out_sequence_number()
        data_list = []
        for p in players_list:
            position_x = int(p.x)+world_x_max+1 #18 bits, coordinates -131072 to 131071
            position_y = int(p.y)+world_x_max+1
            data = position_x << 18 | position_y
            reserved_and_destroyed = int(p.destroyed)
            data = data << 2 | reserved_and_destroyed
            data = data << 2 | self.convert_direction_to_digit(p.direction)
            data = data.to_bytes(5, 'big')
            player_id_number = p.player_id.to_bytes(2, 'big')
            data_list.append(player_id_number)
            data_list.append(data)
        sequence_num = out_sequence_number.to_bytes(1, 'big')
        data_list.append(sequence_num)
        data = b''.join(data_list)
        for p in players_list:
            sock.sendto(data, p.addr)
            sock.sendto(data, p.addr)
            sock.sendto(data, p.addr)
            
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

class player():

    def __init__(self, addr, player_id):
        self.addr = addr
        self.player_id = player_id
        self.x = 0
        self.y = 0
        self.direction = 180
        self.shoot_amount = 0
        self.playerrect = player_sprite.get_rect()
        self.out_sequence_number = -1
        self.destroyed = False
        self.collision_checked = False

    def move(self):
        if (self.direction == 0):
            self.y += distance
            if (self.y > world_x_max):
                self.y = world_x_max
        elif (self.direction == 90):
            self.x += distance
            if (self.x > world_x_max):
                self.x = world_x_max
        elif (self.direction == 180):
            self.y -= distance
            if (self.y < world_x_min):
                self.y = world_x_min
        elif (self.direction == 270):
            self.x -= distance
            if (self.x < world_x_min):
                self.x = world_x_min
        self.playerrect.center = (self.x, self.y)

class bullet():
    
    def __init__(self, player_id, x, y, direction):
        self.player_id = player_id
        self.direction = direction
        self.time = 20
        self.x = x
        self.y = y
        self.bullet_rect = pygame.Rect(0,0,0,0)
        length = 65
        offset = int(player_sprite.get_height()/2)+int(length/2)+2

        if (self.direction == 0):
            self.y += offset
            self.bullet_rect = pygame.Rect(0,0,13,length)
        elif (self.direction == 90):
            self.x += offset
            self.bullet_rect = pygame.Rect(0,0,length,13)
        elif (self.direction == 180):
            self.y -= offset
            self.bullet_rect = pygame.Rect(0,0,13,length)
        elif (self.direction == 270):
            self.x -= offset
            self.bullet_rect = pygame.Rect(0,0,length,13)
        self.bullet_rect.center = (self.x, self.y)
        
    def move(self):
        if (self.direction == 0):
            self.y += bullet_distance
        elif (self.direction == 90):
            self.x += bullet_distance
        elif (self.direction == 180):
            self.y -= bullet_distance
        elif (self.direction == 270):
            self.x -= bullet_distance
        self.bullet_rect.center = (self.x, self.y)

main()
