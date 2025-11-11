from pymycobot import MyCobot280
import time as t


mc = MyCobot280('/dev/ttyAMA0',1000000)
mc.power_on()
mc.send_angles([0.61, 45.87, -92.37, -41.3, 2.02, 9.58], 20)
t.sleep(2.5)
