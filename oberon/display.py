from sys import stderr
import pygame
from pygame.locals import *
from util import bint


size = width, height = 1024, 768

DISPLAY_START = 0xe7f00
DISPLAY_SIZE = width * height / 32

words_in_horizontal_scanline = width / 32


def iter_coords_of_word(address):
  word_x, word_y = divmod(address, words_in_horizontal_scanline)
  pixel_y = word_y * 32
  for y in range(pixel_y, pixel_y + 32):
    yield word_x, y


def update_screen(screen, address, value):
  value = bint(value)
  bits = (value[i] for i in range(32))
  coords = iter_coords_of_word(address)
  for (x, y), bit in zip(coords, bits):
    screen.set_at((y, x), 0xff * (1 - bit))


class ScreenRAMMixin(object):

  def set_screen(self, screen):
    self.screen = screen

  def put(self, address, word):
    super(ScreenRAMMixin, self).put(address, word)
    if DISPLAY_START <= address < DISPLAY_START + DISPLAY_SIZE:
      print >> stderr, 'updating display ram 0x%08x: %s' % (address, bin(word)[2:])
      address -= DISPLAY_START
      update_screen(self.screen, address >> 2, word)
      pygame.display.flip()

  def __setitem__(self, key, value):
    self.put(key, value)


if __name__ == '__main__':
  from traceback import print_exc
  from risc import ByteAddressed32BitRAM, RISC
  from devices import LEDs, FakeSPI, Disk, clock, Mouse
  from bootloader import bootloader

  pygame.init()
  screen = pygame.display.set_mode(size, 0, 8)

  class Memory(ScreenRAMMixin, ByteAddressed32BitRAM):
    pass

  memory = Memory()
  memory.set_screen(screen)

  disk = Disk('disk.img')

  risc_cpu = RISC(bootloader, memory)
  risc_cpu.screen_size_hack()

  risc_cpu.io_ports[0] = clock()
  risc_cpu.io_ports[4] = LEDs()
  risc_cpu.io_ports[20] = fakespi = FakeSPI()
  risc_cpu.io_ports[16] = fakespi.data
  risc_cpu.io_ports[24] = mouse = Mouse()

  mouse.set_coords(450, 474) # Imitate values in C trace.

  fakespi.register(1, disk)

  n = 0
  while n < 8000000:
    n += 1
    if not n % 1000:
      pygame.display.flip()

    try:
      risc_cpu.cycle()
    except:
      print_exc()
      risc_cpu.dump_ram()
      break
