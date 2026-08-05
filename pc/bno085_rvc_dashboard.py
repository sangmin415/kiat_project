"""BNO085 UART-RVC live monitor for the iCE40/RV32I three-axis gimbal."""
from __future__ import annotations
import argparse, math, time
from collections import deque
import pygame
try:
    import serial
except ImportError:
    serial = None

W, H = 1280, 760
BG, PANEL, TEXT, GRID = (7,22,42), (15,48,82), (234,243,250), (42,82,120)
GOLD, CYAN, ORANGE, RED, GREEN = (210,184,128), (94,218,234), (255,171,74), (239,89,101), (104,218,153)

class RvcParser:
    def __init__(self):
        self.buf = bytearray()
        self.bad_checksum = 0
    def feed(self, data):
        self.buf.extend(data); out = []
        while True:
            start = self.buf.find(b"\xaa\xaa")
            if start < 0:
                self.buf[:] = b"\xaa" if self.buf.endswith(b"\xaa") else b""
                return out
            if start: del self.buf[:start]
            if len(self.buf) < 19: return out
            frame = bytes(self.buf[:19]); del self.buf[:19]
            if sum(frame[2:18]) & 255 != frame[18]:
                self.bad_checksum += 1; continue
            value = lambda i: int.from_bytes(frame[i:i+2], "little", signed=True)
            out.append(dict(seq=frame[2], yaw=value(3)/100, pitch=value(5)/100, roll=value(7)/100,
                            ax=value(9), ay=value(11), az=value(13)))
def sim(t, seq):
    return dict(seq=seq & 255, roll=14*math.sin(t*.8), pitch=10*math.sin(t*.5+.7),
                yaw=35*math.sin(t*.2), ax=int(70*math.sin(t*5)), ay=int(60*math.sin(t*4)),
                az=1000+int(45*math.sin(t*6)))
def clamp(x, lo, hi): return max(lo, min(hi, x))
def card(screen, f1, f2, rect, name, val, color):
    pygame.draw.rect(screen, PANEL, rect, border_radius=12)
    pygame.draw.rect(screen, color, rect, 2, border_radius=12)
    screen.blit(f1.render(name, True, color), (rect.x+14, rect.y+12))
    screen.blit(f2.render(f"{val:+06.2f} deg", True, TEXT), (rect.x+14, rect.y+43))
def trace(screen, font, rect, values, color, title, scale):
    pygame.draw.rect(screen, PANEL, rect, border_radius=10)
    screen.blit(font.render(title, True, TEXT), (rect.x+12, rect.y+10))
    for k in range(1, 4):
        y = rect.y + rect.height*k//4; pygame.draw.line(screen, GRID, (rect.x,y),(rect.right,y),1)
    if len(values) > 1:
        pts = [(rect.x + i*(rect.width-1)//(len(values)-1),
                rect.centery-int(clamp(v/scale,-1,1)*rect.height*.35)) for i,v in enumerate(values)]
        pygame.draw.lines(screen, color, False, pts, 2)
def stage(screen, font, small, rect, s):
    pygame.draw.rect(screen, PANEL, rect, border_radius=12)
    pygame.draw.rect(screen, GOLD, rect, 2, border_radius=12)
    screen.blit(font.render("3-AXIS GIMBAL / WAFER STAGE", True, TEXT), (rect.x+16,rect.y+14))
    screen.blit(small.render("R0=Roll   R1=Pitch   R2=Yaw   |   FPGA keypad A: servo zero", True, GOLD), (rect.x+16,rect.y+45))
    cx, cy = rect.centerx, rect.centery+25
    pygame.draw.arc(screen, GOLD, (cx-150,cy-105,300,210), math.radians(180-clamp(s["yaw"],-45,45)), math.radians(360-clamp(s["yaw"],-45,45)), 7)
    pygame.draw.rect(screen, ORANGE, (cx-120+int(s["pitch"]),cy-72,240,145), 6, border_radius=12)
    plate = pygame.Rect(cx-90+int(s["pitch"]),cy-40+int(s["roll"]),180,80)
    pygame.draw.rect(screen, (26,92,111), plate, border_radius=10); pygame.draw.rect(screen,CYAN,plate,4,border_radius=10)
    tag = font.render("WAFER STAGE", True, TEXT); screen.blit(tag,(plate.centerx-tag.get_width()//2,plate.centery-tag.get_height()//2))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port"); ap.add_argument("--baud",type=int,default=115200); ap.add_argument("--simulate",action="store_true")
    a=ap.parse_args()
    if not a.simulate and not a.port: ap.error("use --simulate or --port COMxx (/dev/ttyUSB1 in WSL)")
    if not a.simulate and serial is None: raise RuntimeError("Install pyserial first.")
    uart = None if a.simulate else serial.Serial(a.port,a.baud,timeout=0)
    pygame.init(); screen=pygame.display.set_mode((W,H)); pygame.display.set_caption("PURDUE KIAT | BNO085 FPGA GIMBAL MONITOR")
    title=pygame.font.SysFont("consolas",27,True); label=pygame.font.SysFont("consolas",18,True); value=pygame.font.SysFont("consolas",30,True)
    clock=pygame.time.Clock(); rvc=RvcParser(); sample=sim(0,0); seq=0; next_sim=0; last_rx=0
    hist={x:deque(maxlen=150) for x in ("roll","pitch","yaw","vib")}
    running=True
    while running:
        for e in pygame.event.get():
            if e.type==pygame.QUIT or (e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE): running=False
        now=time.monotonic()
        fresh=[]
        if a.simulate and now>=next_sim:
            seq+=1; fresh=[sim(now,seq)]; next_sim=now+.01
        elif not a.simulate: fresh=rvc.feed(uart.read(uart.in_waiting or 1))
        if fresh:
            sample=fresh[-1]; last_rx=now
            for p in fresh:
                hist["roll"].append(p["roll"]); hist["pitch"].append(p["pitch"]); hist["yaw"].append(p["yaw"])
                hist["vib"].append(math.sqrt(p["ax"]**2+p["ay"]**2+(p["az"]-1000)**2))
        screen.fill(BG); screen.blit(title.render("PURDUE KIAT | BNO085 FPGA GIMBAL MONITOR",True,GOLD),(28,18))
        live=a.simulate or now-last_rx<.5
        screen.blit(label.render("SIMULATION" if a.simulate else ("HARDWARE: "+a.port),True,CYAN if a.simulate else ORANGE),(30,57))
        for i,(n,k,c) in enumerate((("ROLL / R0","roll",CYAN),("PITCH / R1","pitch",ORANGE),("YAW / R2","yaw",GOLD))):
            card(screen,label,value,pygame.Rect(28+i*220,94,205,92),n,sample[k],c)
        status=pygame.Rect(700,94,552,92); pygame.draw.rect(screen,PANEL,status,border_radius=12)
        screen.blit(label.render("RVC VALID" if live else "WAITING FOR RVC DATA",True,GREEN if live else RED),(status.x+14,status.y+12))
        screen.blit(label.render(f"SEQ {sample['seq']:03d}  checksum errors {rvc.bad_checksum}  ACC {sample['ax']}, {sample['ay']}, {sample['az']} mg",True,TEXT),(status.x+14,status.y+54))
        stage(screen,label,pygame.font.SysFont("consolas",14,True),pygame.Rect(28,205,790,525),sample)
        trace(screen,label,pygame.Rect(842,205,410,115),hist["roll"],CYAN,"ROLL - degrees",35)
        trace(screen,label,pygame.Rect(842,338,410,115),hist["pitch"],ORANGE,"PITCH - degrees",35)
        trace(screen,label,pygame.Rect(842,471,410,115),hist["yaw"],GOLD,"YAW - degrees",60)
        trace(screen,label,pygame.Rect(842,604,410,126),hist["vib"],RED,"ACCELERATION VIBRATION - mg",300)
        pygame.display.flip(); clock.tick(60)
    if uart: uart.close()
    pygame.quit()
if __name__=="__main__": main()
