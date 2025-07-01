import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100
HEIGHT = 650
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    yoko, tate = True, True
    
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    delta = {
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self.imgs = {
            (+1, 0): img,
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),
            (-1, 0): img0,
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"  #通常状態
        self.hyper_life = 0  #無敵状態の残りフレーム数

    def change_img(self, num: int, screen: pg.Surface):
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        # 機能1: 高速化
        # 左Shiftキーが押されている間、スピードを20に、それ以外は10にする 
        self.speed = 20 if key_lst[pg.K_LSHIFT] else 10

        sum_mv = [0, 0]
        
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
                
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
            
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            
        if self.state == "hyper":  #無敵状態のとき
            self.hyper_life -= 1
            self.image = pg.transform.laplacian(self.imgs[self.dire])  #こうかとん透明化
            
            if self.hyper_life <= 0:  #無敵状態が切れたら戻す
                self.state = "normal"
                self.image = self.imgs[self.dire]
                
        else:
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)

class Bomb(pg.sprite.Sprite):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        super().__init__()
        rad = random.randint(10, 50)
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    # 機能6: 弾幕
    def __init__(self, bird: Bird, angle_offset: int = 0):
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx)) + angle_offset
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        
        if check_bound(self.rect) != (True, True):
            self.kill()

# 機能6: 弾幕のためのヘルパークラス
class NeoBeam:
    """
    弾幕を生成するクラス
    """
    def __init__(self, bird: Bird, num: int):
        self.bird = bird
        self.num = num

    def gen_beams(self) -> list[Beam]:
        beams = []
        if self.num > 1:
            step = 100 / (self.num - 1)
            for i in range(self.num):
                angle = -50 + step * i
                beams.append(Beam(self.bird, angle))
        else: # ビームが1つの場合
             beams.append(Beam(self.bird, 0))
        return beams

class Explosion(pg.sprite.Sprite):
    def __init__(self, obj: "Bomb|Enemy", life: int):
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)
        self.state = "down"
        self.interval = random.randint(50, 300)

    def update(self):
        
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 100000
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


# 機能5: 防御壁
class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス
    """
    def __init__(self, bird: Bird, life: int):
        super().__init__()
        self.life = life
        # こうかとんの向きに合わせて防御壁の角度と位置を決定
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.Surface((20, bird.rect.height * 2))
        pg.draw.rect(self.image, (0, 0, 255), self.image.get_rect())
        self.image.set_colorkey((0, 0, 0)) # 黒色部分を透明化
        self.image = pg.transform.rotozoom(self.image, angle, 1.0)
        self.rect = self.image.get_rect()
        self.rect.center = bird.rect.centerx + bird.rect.width * self.vx, bird.rect.centery + bird.rect.height * self.vy
    
    def update(self, bird: Bird):
        self.life -= 1
        # こうかとんに追従させる
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        # Surfaceを毎回作り直して回転させる
        base_image = pg.Surface((20, bird.rect.height * 2))
        pg.draw.rect(base_image, (0, 0, 255), base_image.get_rect())
        base_image.set_colorkey((0,0,0))
        self.image = pg.transform.rotozoom(base_image, angle, 1.0)
        self.rect = self.image.get_rect()
        self.rect.center = bird.rect.centerx + bird.rect.width * self.vx, bird.rect.centery + bird.rect.height * self.vy
        
        if self.life < 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()

    # 機能5: 防御壁のグループ
    shields = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    
    while True:
        key_lst = pg.key.get_pressed()
        
        for event in pg.event.get():
            
            if event.type == pg.QUIT:
                return 0
            
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                # 機能6: 弾幕
                if key_lst[pg.K_LSHIFT]:
                    beams.add(NeoBeam(bird, 5).gen_beams())
                else:
                    beams.add(Beam(bird))
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))

        # 無敵状態発動処理（右Shift＋スコア100超で発動）
        if key_lst[pg.K_RSHIFT] and score.value > 100 and bird.state == "normal":
            bird.state = "hyper"
            bird.hyper_life = 500
            score.value -= 100

                # 機能5: 防御壁の発動
                if event.key == pg.K_s and score.value >= 50 and len(shields) == 0:
                    score.value -= 50
                    shields.add(Shield(bird, 400))

        screen.blit(bg_img, [0, 0])

        if tmr % 200 == 0:
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        # 機能5: 防御壁と爆弾の衝突判定
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))  # 衝突しても爆発エフェクトだけ発生
                score.value += 1
                
            else:
                bird.change_img(8, screen)
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        # 機能5: 防御壁の更新と描画
        shields.update(bird)
        shields.draw(screen)
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()