# WRO Future Engineers Autonomous Vehicle – ESP32 MicroPython User Guide

## 1. Project Overview

This repository documents and stores the software, wiring notes, calibration process, and usage instructions for an autonomous vehicle prototype built for a Future Engineers style robotics challenge. The robot is based on an ESP32 running MicroPython and combines a simple car platform with several sensors and motion-control modules. The goal of the project is to create a vehicle that can be tested manually, calibrated step by step, and then improved toward autonomous driving behavior.

The vehicle was built using an ESP32 microcontroller, an ELECFREAKS Wonder Building Kit structure, two Arduino-style geared DC motors, one H-bridge motor driver, one gyroscope/IMU module, four ultrasonic distance sensors, one WonderCam vision module, and one magnetic encoder. The current codebase is intentionally simple and modular. It separates hardware control from vehicle movement logic and from manual-control input. This makes the project easier to understand, easier to debug, and more suitable for students who are learning robotics, MicroPython, and autonomous vehicle design.

This README is written as a practical guide. It explains the repository structure, the purpose of each source file, the hardware modules, the recommended wiring workflow, the software installation process, the procedure for copying the code to the ESP32, and the basic testing and calibration stages. It is not only a description of the final robot; it is also a working guide for building, testing, and improving the robot safely.

The project is designed around the idea that a robot should first be understandable before it becomes complex. Instead of starting with advanced artificial intelligence or fully automatic navigation, the project begins with reliable hardware abstraction: moving the servo, controlling the motors, reading sensors, and receiving control information. Once these foundations are stable, the same structure can be expanded into wall-following, obstacle avoidance, color recognition, line detection, zone recognition, odometry, and autonomous route decisions.

The current robot can be used in several modes of development. First, it can be driven manually through UART commands coming from an external controller, such as a PS4 controller interface. Second, the motor and steering functions can be called directly from MicroPython for simple movement tests. Third, the sensors can be read independently for calibration and debugging. Finally, the movement layer can be expanded into autonomous routines that combine distance readings, gyroscope angle updates, camera detections, and encoder feedback.

This repository follows a documentation-oriented structure similar to engineering-materials repositories used in robotics competitions. The source code is placed in the `src` folder, while photos, diagrams, mechanical models, testing notes, and strategy documents are placed in their own folders. This helps separate the robot program from the engineering evidence required to explain how the robot was built and how it works.

---

## 2. Main Objectives

The first objective of this project is to build a functional robotic vehicle that can move forward, move backward, steer left and right, stop safely, and be controlled during testing. The second objective is to create a clean code structure where each hardware component is represented by a class. The third objective is to prepare the system for autonomous navigation by collecting useful data from sensors such as ultrasonic distance sensors, a gyroscope, an encoder, and a vision module.

The robot is not treated as a single block of code. Instead, each part of the system has a responsibility. The servo class controls steering. The motor class controls speed and direction through the H-bridge. The ultrasonic sensor class measures distance. The encoder class measures wheel rotation. The gyroscope class estimates angular movement. The camera class communicates with the WonderCam module through I2C. The vehicle movement class connects these components and provides a higher-level interface. The UART controller class interprets remote-control input.

The project also has an educational objective. Students should be able to open the source files and understand what each class does. They should see how real-world robotics programs are organized: hardware drivers at the bottom, movement logic in the middle, and behavior or strategy at the top. This approach avoids mixing all the logic into one large file and makes future improvements easier.

A final objective is to create a repository that can be presented as an engineering project. For that reason, this README explains how to prepare the folders, how to document the robot, how to add photos and diagrams, and how to describe testing results. A robotics repository should not contain only code. It should also show the mechanical design, electronic layout, sensor placement, calibration values, and reasoning behind the decisions.

---

## 3. Hardware Used

The robot uses the following main components:

- ESP32 development board running MicroPython
- ELECFREAKS Wonder Building Kit mechanical structure
- Two Arduino-style DC geared motors
- One H-bridge motor driver
- One steering servo
- One gyroscope/IMU module
- Four ultrasonic sensors
- One WonderCam vision module
- One magnetic encoder
- Two 3.7 V bateries to power source for motors
- Jumper wires and common ground connections
- Optional external controller interface using UART (just for debug)

The ESP32 is the main controller. It reads sensors, sends PWM signals, controls motor direction pins, communicates through I2C, and receives UART data. The ELECFREAKS Wonder Building Kit provides a mechanical structure that can be adapted for the vehicle chassis, sensor mounts, camera support, and wiring organization.

The two geared motors provide traction. Depending on the mechanical setup, both motors may be connected to the same H-bridge channel or to separate motor channels if the driver supports it. In the current simplified design, movement is controlled through an H-bridge using direction pins and a PWM enable pin. The motor driver is necessary because the ESP32 cannot power motors directly. The ESP32 only sends control signals; the motor driver handles the higher current required by the motors.

The steering servo controls the direction of the front wheels. In the current configuration, the servo is calibrated using microsecond pulse limits and a center value. The steering geometry is represented in the vehicle configuration so that a requested wheel angle can be converted into a servo angle.

The gyroscope/IMU is used to estimate the robot’s rotation. This is useful for turns, orientation correction, and future autonomous navigation. Since gyroscopes usually drift, the software includes a calibration step to calculate the bias before using angular readings.

The four ultrasonic sensors can be placed around the vehicle to measure distances in front, behind, left, and right. These sensors help prevent collisions, detect walls, follow corridors, identify open areas, and support turning decisions.

The WonderCam vision module is included to detect visual features such as colors, lines, or learned patterns depending on its active mode. In the current structure, communication with the camera is done through I2C. The camera can become a major part of the autonomous navigation strategy once the low-level movement and sensor systems are stable.

The encoder measures wheel rotation. It is useful for estimating distance traveled. While odometry is not perfect because wheels can slip, encoder data is still valuable for measuring movement, testing consistency, and combining with gyroscope data.

---

The `src/esp32-micropython` folder contains the files that are copied to the ESP32. These are the files that the microcontroller needs in order to run the robot. The documentation folders should not be copied to the ESP32 because they may contain images, models, and large files.

The `schemes` folder should contain wiring diagrams, pin tables, and sensor-position diagrams. It is very important to document which ESP32 pins are connected to each sensor or actuator. This prevents confusion when the robot is repaired or modified.

The `models` folder should contain mechanical design files. These may include 3D models, STL files, CAD files, or simple drawings. If no 3D models are available yet, this folder can still include measurements and photos of the chassis.

The `other` folder is for engineering notes. This is where calibration values, test results, development decisions, and strategy explanations should be stored. For example, if a certain ultrasonic threshold works better for wall following, it should be written down in `testing-notes.md` or `calibration.md`.

The `t-photos` folder is for team photos, while `v-photos` is for vehicle photos. The `video` folder can contain a text file with a link to a demonstration video.

---

## 4. Source Code Files

### `boot.py`

The `boot.py` file is executed automatically by MicroPython when the ESP32 starts. In this project, it is kept minimal. This is a good practice because the robot should not execute complex logic at boot before the hardware is ready. The main robot behavior should stay in `main.py`.

A minimal `boot.py` also makes debugging easier. If something goes wrong in the main program, the board is less likely to become difficult to access because of complex startup behavior.

### `main.py`

The `main.py` file is the entry point of the robot program. It imports the required MicroPython modules, imports the component classes, defines the ESP32 pins, creates objects for the servo, motor, sensors, UART, and vehicle movement, and starts the main loop.

The main loop currently updates the UART controller repeatedly. This allows the robot to respond to commands from the external controller. During manual testing, this is very useful because it allows the team to test motors, steering, speed response, and general mechanical behavior before enabling autonomous functions.

The file also initializes the I2C bus and prints the result of `i2c.scan()`. This is important for checking whether I2C devices such as the gyroscope, encoder, or camera are detected.

### `componentes.py`

The `componentes.py` file contains hardware component classes. This file is the hardware abstraction layer of the project. Instead of writing raw pin instructions everywhere, the code creates classes such as `Servo`, `MotorPuenteH`, `SonarBit`, `Encoder_AS5600`, `BMI160`, `TCS3200`, and `WonderCam`.

This structure is useful because each class hides the low-level details of a device. For example, the servo class knows how to convert an angle into PWM duty. The motor class knows how to set the H-bridge direction pins and PWM speed. The ultrasonic class knows how to trigger a pulse and measure echo time. The gyroscope class knows how to initialize registers and integrate angular velocity. The WonderCam class knows how to read camera registers over I2C.

### `movimiento_vehiculo.py`

The `movimiento_vehiculo.py` file contains the vehicle-level movement logic. This is where individual components are combined into a vehicle object. It includes a `ConfigVehiculo` class for geometry, tolerances, calibration values, servo limits, wheel perimeter, and speed settings.

The `MovimientoDelVehiculo` class receives objects such as the motor, servo, encoder, and IMU. It can then offer methods for steering, centering, odometry updates, and distance-based movements. This file is the correct place to add simple movement functions such as `move_forward`, `move_backward`, `turn_left`, `turn_right`, and later autonomous behaviors.

### `ps4_uart.py`

The `ps4_uart.py` file reads and interprets UART messages from an external controller interface. The code expects formatted packets containing connection state, stick value, directional buttons, button values, and trigger values. The class converts stick input into steering direction and trigger input into motor speed.

This file is useful during the development phase because manual driving helps verify the mechanical build. Before trusting an autonomous algorithm, the robot must be able to move reliably under manual control.

### `CMD.md`

The `CMD.md` file documents useful `mpremote` commands. It explains how to list files on the ESP32, copy files to the microcontroller, copy a folder, and run `main.py` from the computer. This file is part of the user guide and should be kept updated as the project changes.

---

## 5. Software Requirements

To use this project, the computer should have Python installed. The `mpremote` tool is used to communicate with the ESP32 running MicroPython. If `mpremote` is not installed, it can be installed with:

```bash
python -m pip install mpremote
```

The ESP32 must already have MicroPython firmware installed. If the board does not have MicroPython, it must be flashed first using a tool such as `esptool`. After flashing, the board should appear as a serial device on the computer. On Windows, it may appear as `COM5`, `COM6`, or another COM port. On Linux or macOS, it may appear as `/dev/ttyUSB0`, `/dev/ttyACM0`, or a similar device.

To verify the connection, run:

```bash
python -m mpremote connect COM5 ls
```

Replace `COM5` with the correct port for your computer. If the command lists files on the ESP32, communication is working.

---

## 6. Copying the Code to the ESP32

Only the MicroPython source files should be copied to the ESP32. Do not copy the entire repository, because folders such as `v-photos`, `models`, and `video` may contain large files that are not needed by the microcontroller.

From the root of the repository, enter the source folder:

```bash
cd src/esp32-micropython
```

Then copy the required files:

```bash
python -m mpremote connect COM5 cp boot.py :boot.py
python -m mpremote connect COM5 cp main.py :main.py
python -m mpremote connect COM5 cp componentes.py :componentes.py
python -m mpremote connect COM5 cp movimiento_vehiculo.py :movimiento_vehiculo.py
python -m mpremote connect COM5 cp ps4_uart.py :ps4_uart.py
```

After copying the files, verify that they are on the ESP32:

```bash
python -m mpremote connect COM5 ls
```

To run the program manually from the computer:

```bash
python -m mpremote connect COM5 run main.py
```

If `main.py` exists on the ESP32, it will also run automatically when the board is reset or powered on.

---

## 7. Recommended Pin Documentation

The actual pin configuration may change depending on the vehicle wiring. The project should include a pin table in `schemes/pin-table.md`. A recommended table format is:

```markdown
# ESP32 Pin Table

| Function | ESP32 Pin | Notes |
|---|---:|---|
| Servo steering | GPIO 27 | PWM, 50 Hz |
| Motor ENA | GPIO 15 | PWM speed control |
| Motor IN1 | GPIO 4 | H-bridge direction |
| Motor IN2 | GPIO 2 | H-bridge direction |
| I2C SDA | GPIO 21 | Shared I2C bus |
| I2C SCL | GPIO 22 | Shared I2C bus |
| UART RX2 | GPIO 16 | Receives controller data |
| UART TX2 | GPIO 17 | Sends controller data if needed |
| Ultrasonic front trigger | GPIO 5 | Distance sensor |
| Ultrasonic front echo | GPIO 18 | Distance sensor |
| Ultrasonic rear trigger | GPIO 12 | Distance sensor |
| Ultrasonic rear echo | GPIO 14 | Distance sensor |
```

Because the robot uses several sensors, it is very important to keep this table updated. If a pin is reused accidentally, the robot may behave incorrectly or a device may stop working. For example, one common mistake is using the same GPIO for a motor direction pin and a servo signal. Always check the pin table before adding new components.

---

## 8. Power and Safety Notes

The ESP32 should not power the motors directly. Motors require more current than the ESP32 pins can provide. The H-bridge should be connected to the motor power supply, while the ESP32 should provide only logic signals.

Always connect the grounds together. The motor power supply ground, H-bridge ground, and ESP32 ground should share a common reference. Without a common ground, the control signals may not be interpreted correctly.

Be careful with voltage levels. The ESP32 uses 3.3 V logic. Some modules accept 3.3 V signals, while others may use 5 V. Before connecting a sensor or module, verify its required voltage. If a module outputs 5 V on a signal pin, it may damage the ESP32 unless a level shifter or voltage divider is used.

When testing motors for the first time, lift the robot so the wheels do not touch the table. This prevents the robot from suddenly moving and falling. Test low speeds first. Verify direction before increasing speed.

When testing the servo, disconnect the mechanical linkage or lift the front wheels if necessary. Incorrect servo limits can force the steering mechanism beyond its physical range and damage the servo or chassis.

---

## 9. First Startup Procedure

Before running the full robot program, follow this startup checklist:

1. Inspect the wiring.
2. Confirm that the motor power supply is connected correctly.
3. Confirm that the ESP32 is powered safely.
4. Confirm that all grounds are connected.
5. Check that the servo signal wire is connected to the correct pin.
6. Check that the H-bridge inputs are connected to the correct pins.
7. Check I2C wiring: SDA to SDA, SCL to SCL.
8. Check ultrasonic trigger and echo pins.
9. Connect the ESP32 to the computer.
10. Run `mpremote ls` to confirm communication.
11. Run a simple I2C scan.
12. Run `main.py` and observe printed output.
13. If anything overheats, disconnect power immediately.

A good first test is to run the program with the wheels lifted. Watch the serial output. If the I2C scan prints addresses, at least one I2C device is responding. If the program crashes, read the error message carefully. Most errors are caused by wiring mistakes, missing files, wrong pin numbers, or a sensor not responding.

---

## 10. Manual Control Testing

Manual control is useful before autonomous testing. The robot should be able to drive forward, backward, turn left, turn right, and stop. If the project uses a PS4 controller through an external UART interface, the UART messages should be checked first.

A valid UART packet should arrive as a line of text. The parser expects a specific format. If the format changes, the parser in `ps4_uart.py` must be updated. During debugging, enable debug prints in the main loop so the robot prints the received state and the calculated objectives.

Manual testing should verify:

- The right trigger increases forward speed.
- The left trigger increases reverse speed.
- The steering stick moves the servo left and right.
- Releasing the steering stick returns the servo to center.
- Releasing the triggers stops the motor.
- The robot does not continue accelerating after communication stops.
- The motor direction matches the intended movement.

If the robot moves backward when it should move forward, swap the motor wires or change the direction logic in the motor class. If the steering is reversed, change the sign mapping in the UART controller or adjust the servo conversion in the vehicle movement class.

---

## 11. Servo Calibration

Servo calibration is one of the most important steps because steering errors affect every movement. The servo is controlled by PWM at 50 Hz. The code maps angles into pulse widths using minimum and maximum microsecond values.

The project currently uses a steering center value in the configuration. For many car-style robots, the mechanical center is not the same as the mathematical center of the servo. Therefore, the center must be found experimentally.

Recommended calibration process:

1. Lift the front of the robot.
2. Send the servo to the current center value.
3. Observe the front wheels.
4. If the wheels point left, adjust the center value.
5. If the wheels point right, adjust the center value.
6. Repeat until the wheels are physically straight.
7. Test left and right extremes.
8. Make sure the mechanism does not force the servo at the extremes.
9. Save the final center and limits in the configuration.

The configuration should include:

- `servo_centro`
- `servo_izquierda_max`
- `servo_derecha_max`
- `angulo_rueda_max_deg`
- `paso_servo`

A small steering step is useful for smooth manual control. A large steering step is useful for fast turning but may make the robot unstable.

---

## 12. Motor Testing

The DC motors are controlled through an H-bridge. The H-bridge uses two direction pins and one PWM enable pin. The motor class limits speed values to a safe PWM range and applies acceleration changes.

Motor testing should be done gradually. Begin with a low PWM value, such as 200 or 300. Check whether the wheels rotate. If the motors do not move, increase the value slowly. Some geared motors require a minimum PWM value before they overcome friction.

Recommended motor tests:

1. Test motor stop.
2. Test forward direction at low speed.
3. Test reverse direction at low speed.
4. Test acceleration from zero.
5. Test deceleration to zero.
6. Test changing from forward to reverse.
7. Test stopping under load.
8. Test with the robot on the floor.

If the robot is too aggressive, reduce `velocidad_crucero` and `velocidad_giro`. If the robot cannot start moving, increase the minimum speed or use a stronger battery. If the H-bridge becomes hot, check motor current and driver capacity.

---

## 13. Ultrasonic Sensor Usage

The robot includes four ultrasonic sensors. These sensors measure distance by sending a sound pulse and measuring the echo time. They are useful for detecting walls, obstacles, and open spaces.

A practical placement is:

- Front sensor: detects obstacles ahead.
- Rear sensor: detects obstacles behind.
- Left sensor: measures distance to the left wall.
- Right sensor: measures distance to the right wall.

With four sensors, the robot can implement simple wall-following logic. For example, if the left distance is much smaller than the right distance, the robot may be too close to the left wall and should steer slightly right. If the right distance is much smaller than the left distance, the robot may be too close to the right wall and should steer slightly left.

Ultrasonic sensors can produce noisy readings. It is recommended to read each sensor several times and use an average, median, or filtered value. The program should also handle invalid readings. If a sensor returns `None`, the robot should not make a strong decision from that reading.

For autonomous behavior, useful thresholds may include:

- Minimum safe front distance
- Desired side distance
- Maximum side difference
- Curve detection distance jump
- Sensor timeout value

A simple rule is better than a complex one during early testing. For example:

```text
If front distance is too small, stop.
Else if left side is too close, steer right.
Else if right side is too close, steer left.
Else go straight.
```

This basic behavior can later be improved with gyroscope-supported turns and camera-based zone recognition.

---

## 14. Gyroscope and IMU Calibration

The gyroscope measures angular velocity. By integrating angular velocity over time, the program can estimate the robot’s angle. This is useful for turning and orientation correction. However, gyroscopes have bias. Even when the robot is not moving, the gyroscope may report a small angular velocity. If this bias is not corrected, the estimated angle will drift.

The project includes a calibration function that samples the gyroscope while the robot is still. During this process, the robot must not move. The average measured value is stored as the bias and subtracted from future readings.

Recommended gyroscope calibration process:

1. Place the robot on a stable surface.
2. Do not touch the robot.
3. Start the calibration routine.
4. Wait until calibration finishes.
5. Begin movement tests only after calibration.
6. If the angle drifts too quickly, recalibrate.

For turning, the gyroscope can be used to stop a turn when the desired angle is reached. For example, the robot can steer left and move forward until the IMU reports approximately 90 degrees of rotation. This is usually better than relying only on time because battery voltage and surface friction affect movement speed.

---

## 15. Encoder Usage

The encoder measures rotation. If the encoder is attached to a wheel or axle, the program can estimate distance traveled using the wheel perimeter. The basic formula is:

```text
distance = wheel_rotations × wheel_perimeter
```

The code stores wheel perimeter in the vehicle configuration. If the wheel perimeter is wrong, the distance estimate will also be wrong. Therefore, the wheel should be measured carefully.

Recommended encoder calibration process:

1. Mark a start line on the floor.
2. Reset the encoder.
3. Move the robot forward a measured distance, such as 50 cm.
4. Read the encoder-estimated distance.
5. Compare real distance and estimated distance.
6. Adjust the distance factor.
7. Repeat several times.

Encoder readings can be affected by wheel slip. For this reason, the encoder should not be the only source of truth. It should be combined with gyroscope readings and sensor feedback.

---

## 16. WonderCam Vision Module

The WonderCam vision module can provide visual information through I2C. Depending on the selected function, it can detect color, lines, tags, or learned visual features. In this project, the camera is treated as a sensor that can provide simplified vision results to the ESP32.

The camera is useful because it can detect things that ultrasonic sensors cannot. For example, ultrasonic sensors can measure distance but cannot identify colors. The camera may help detect track markings, colored zones, obstacle colors, start zones, or turn indicators.

Recommended camera testing process:

1. Connect the camera to the I2C bus.
2. Run an I2C scan and confirm that the camera address appears.
3. Read the firmware version if supported.
4. Check the current active function.
5. Select the desired function manually or through I2C if supported.
6. Train or configure the camera using its built-in interface if required.
7. Read detection results repeatedly.
8. Print raw data before making decisions.
9. Compare camera detections with what is visible on the screen.
10. Add filtering before using detections for movement.

Vision readings may be incomplete or unstable. It is better to confirm the same detection several times before changing robot behavior. For example, if the camera detects a color region, the robot should confirm that the detection appears in multiple frames before treating it as a navigation signal.

---

## 17. Basic Autonomous Strategy

The recommended autonomous strategy should be built in stages. Do not try to create a complete autonomous system in one step.

### Stage 1: Manual Movement

The robot is controlled manually. The goal is to verify hardware, steering, motor response, and power stability.

### Stage 2: Sensor Reading

The robot stays still and prints sensor values. The goal is to understand normal readings, noisy readings, and invalid readings.

### Stage 3: Safety Stop

The robot moves forward slowly and stops if the front ultrasonic sensor detects an obstacle closer than a safe threshold.

### Stage 4: Simple Wall Correction

The robot reads left and right distances. If it is closer to the left wall, it steers right. If it is closer to the right wall, it steers left. If both sides are balanced, it centers the steering.

### Stage 5: Curve Detection

If one side distance suddenly increases while the other side remains reasonable, the robot may be entering a curve or open section. In this case, the robot can start a turn and use the gyroscope to support the turn until the orientation changes enough.

### Stage 6: Vision Events

The camera detects visual markers, color zones, or learned features. These events can be used to count sections, detect special areas, or prepare turns.

### Stage 7: Combined Behavior

The final behavior combines ultrasonic sensors, gyroscope, encoder, and camera. The robot should use the simplest reliable rule at each moment.

The most important principle is that the robot should always have a safe fallback. If the camera reading is unclear, use ultrasonic sensors. If the encoder distance is unreliable, use wall distance and gyroscope angle. If communication or sensor readings fail, stop the motor.

---

## 18. State Machine

A clean autonomous program can be implemented as a state machine. A state machine helps avoid writing confusing nested conditions.

Suggested states:

```text
WAIT_START
MANUAL_TEST
READ_SENSORS
OPEN_CHALLENGE
FOLLOW_WALLS
AVOID_OBSTACLE
TURN_LEFT
TURN_RIGHT
RECOVER_CENTER
STOPPED
```

Each state should have a clear responsibility. For example, `FOLLOW_WALLS` only keeps the robot centered between walls. `TURN_LEFT` only performs a left turn using steering and gyroscope feedback. `RECOVER_CENTER` returns the steering to center and stabilizes the robot after a turn.

A simple loop can look like this:

```python
while True:
    read_sensors()

    if state == "FOLLOW_WALLS":
        follow_walls()
    elif state == "TURN_LEFT":
        turn_left()
    elif state == "TURN_RIGHT":
        turn_right()
    elif state == "STOPPED":
        motor.detener()
```

The advantage of this structure is that students can understand one behavior at a time. It also makes testing easier because each state can be tested separately.

---

## 19. Calibration Files

The `other/calibration.md` file should store the final calibration values. This file is very important because calibration values often change during testing.

Recommended content:

```markdown
# Calibration Notes

## Servo
- Center angle:
- Left maximum:
- Right maximum:
- Steering step:

## Motor
- Minimum useful speed:
- Cruise speed:
- Turn speed:
- Maximum safe speed:

## Ultrasonic Sensors
- Front safe distance
- Left desired distance
- Right desired distance
- Maximum valid distance

## Gyroscope
- I2C address:
- Bias value:
- Noise threshold:
- Turn tolerance:

## Encoder
- Wheel perimeter:
- Distance factor:
- Direction:
```

Every time a value is changed in code, it should also be updated in the calibration file. This helps the team remember what was tested and why a value was chosen.

---

## 21. Testing Notes

The `other/testing-notes.md` file should be used as a development diary. Each test should include the date, the setup, the behavior observed, and the next action.

Example:

```markdown
## Test 01 – Manual Control

Goal:
Verify basic motor and steering response.

Result:
The robot moved forward correctly. Steering left was reversed.

Action:
Invert the steering mapping in the UART controller.
```

Good testing notes are extremely useful because robotics problems often return later. A note that seems unnecessary today can save hours of debugging in the future.

---

## 22. Troubleshooting

### The ESP32 does not appear in `mpremote`

Check the USB cable. Some USB cables only provide power and do not transfer data. Try another cable or USB port. Check the correct COM port.

### The program says a module is missing

Make sure all required `.py` files were copied to the ESP32. If `main.py` imports `componentes.py`, that file must be present on the board.

### The I2C scan shows no devices

Check SDA and SCL wiring. Check power and ground. Check whether the module uses 3.3 V or 5 V. Try a lower I2C frequency, such as 100 kHz.

### The motor does not move

Check motor power. Check the H-bridge enable pin. Check direction pins. Check whether the PWM value is high enough. Check common ground.

### The motor moves in the wrong direction

Swap motor wires or invert the direction logic in the motor class.

### The servo moves incorrectly

Check the signal pin. Check power. Check calibration values. Make sure the servo is not mechanically blocked.

### The robot resets when motors start

The power supply may not provide enough current. Use a separate motor power supply and common ground. Add capacitors if necessary.

### Sensor values are unstable

Read multiple samples and filter the values. Check wiring. Keep motor wires away from sensor wires if possible.

### The camera returns no useful data

Confirm the I2C address. Confirm the active function. Check the camera’s built-in configuration. Print raw register values before adding movement logic.

---

## 23. Development Rules

The project should follow a few simple development rules:

1. Test one component at a time.
2. Do not add autonomous behavior until manual movement is reliable.
3. Keep hardware classes separate from strategy logic.
4. Document every pin.
5. Document every calibration value.
6. Do not copy large documentation folders to the ESP32.
7. Use safe motor speeds during testing.
8. Stop the robot when sensor data is invalid.
9. Prefer simple rules before complex algorithms.
10. Make small changes and test after each change.

These rules make the project safer and easier to understand. They also make the repository more useful for a team because any member can inspect the code and documentation.

---

## 24. Future Improvements

Future versions of this robot may include:

- Full autonomous wall-following mode
- Obstacle avoidance using four ultrasonic sensors
- Gyroscope-supported 90-degree turns
- Encoder-based distance control
- Vision-based detection of colored zones
- Camera-based turn marker detection
- Better filtering for ultrasonic readings
- A complete state machine for the challenge
- Battery monitoring
- Automatic calibration routines
- Data logging during test runs
- Improved mechanical supports for sensors
- More precise steering geometry
- Separate configuration file for all constants

The current structure already supports these improvements because the code is modular. New behavior should be added above the hardware layer, not inside the low-level classes unless the device driver itself needs improvement.

---

## 25. Recommended Workflow for New Users

A new user should follow this order:

1. Read this README completely.
2. Review the wiring diagram.
3. Review the pin table.
4. Connect only the ESP32 and test `mpremote`.
5. Copy the source files to the ESP32.
6. Run `main.py` with motors disconnected.
7. Check I2C scan output.
8. Test the servo alone.
9. Test the motor driver alone.
10. Test ultrasonic sensors one by one.
11. Test the gyroscope.
12. Test the encoder.
13. Test the WonderCam.
14. Enable manual control.
15. Drive the robot at low speed.
16. Adjust servo center.
17. Adjust motor speed.
18. Record calibration values.
19. Add simple safety stop.
20. Add autonomous behavior gradually.

This workflow reduces risk. It also helps identify which component is causing a problem. If everything is connected and tested at once, debugging becomes much harder.

---

## 26. Conclusion

This project is a foundation for an ESP32-based autonomous vehicle using MicroPython. The robot combines mechanical construction, electronics, programming, sensor reading, and movement control. The repository is organized so that the code can run on the ESP32 while the documentation explains how the robot was built and how it should be used.

The most important idea in this project is progressive development. A reliable autonomous robot is not created by writing one large program. It is created by testing small systems, documenting results, calibrating carefully, and combining simple behaviors into a complete strategy.

The current robot includes the essential components needed for future autonomous navigation: motor control, steering control, distance sensing, orientation sensing, wheel rotation measurement, and vision input. With this structure, the team can continue improving the robot step by step while keeping the code understandable and the repository organized.

This README should be updated whenever the robot changes. If a pin changes, update the pin table. If a calibration value changes, update the calibration notes. If a new strategy is tested, document the result. A good engineering repository is not only a place to store code; it is a record of the decisions, tests, and improvements that made the robot work.
