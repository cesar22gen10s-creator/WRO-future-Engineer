# Vehicle Assembly and Software Operation

## Project Overview

This autonomous vehicle was built for the **WRO Future Engineers competition**. The project combines a LEGO-style mechanical structure, ESP32 microcontrollers, distance sensors, an IMU, an encoder, a vision camera, and custom software written mainly in **MicroPython**. 

The goal of the project was not only to build a vehicle capable of completing the competition track, but also to understand how the different parts of an autonomous robot work together.

Together, we were able to develop the program ourselves, using Artificial Intelligence as a support tool during the process. AI was mainly used to help create or understand individual functions and programming ideas. These functions were then tested, modified, calibrated, and connected until they worked correctly with the real vehicle.

Thanks to its modular design, the robot can operate autonomously, but it can also be controlled using a Bluetooth gamepad. This made the vehicle useful both as a competition robot and as a platform for testing and learning.

## Mechanical Construction

The mechanical design was created using **two ELECFREAKS Wonder Building Kits**.

The main inspiration was the steering vehicle shown in the ELECFREAKS Wonder Building Kit documentation:

[https://wiki.elecfreaks.com/en/microbit/building-blocks/wonder-building-kit/Wonder-Building-Kit-case-37/](https://wiki.elecfreaks.com/en/microbit/building-blocks/wonder-building-kit/Wonder-Building-Kit-case-37/)

This model provided us with a simple starting point for the chassis, front steering system, rear motor system, wheels, and LEGO-compatible structure.

After building the basic vehicle, we modified it to adapt it to our project.

The original **micro:bit** and **Wukong expansion board** were removed.

Two ESP32 boards were added to the vehicle.

The first ESP32 became the **main computer of the robot**. It runs MicroPython using the official ESP32 firmware available at:

[https://micropython.org/download/ESP32_GENERIC/](https://micropython.org/download/ESP32_GENERIC/)

This ESP32 is responsible for reading the sensors, deciding what the robot should do, controlling the steering, controlling the motors, and managing autonomous navigation.

The second ESP32 was programmed using the **Arduino IDE** and the **Bluepad32** library. Its main purpose is to connect to a Bluetooth gamepad, such as a PS4 controller, and send the controller information to the main ESP32 through UART.

This second ESP32 was especially useful during development because it allowed the students to take manual control of the vehicle whenever necessary. Instead of modifying the autonomous program every time something needed to be tested, they could simply drive the vehicle using the controller.

## Sensors

Several sensors were added around the vehicle so that the program could understand what was happening around it.

An **AS5600 magnetic encoder** is connected through I2C. It measures the rotation of the drivetrain and allows the program to estimate movement and wheel speed. The software continuously updates the encoder information and calculates values such as accumulated movement and RPM.

A **BMI160 gyroscope and accelerometer** is also connected through I2C. For autonomous navigation, one of its most important functions is tracking the vehicle's orientation, or *heading*. This allows the robot to recognize when it is moving in a straight line and to approximately measure how much it has turned during a corner.

Three **VL53L0X Time-of-Flight (ToF) sensors** are installed on the robot. One points forward, while the other two are oriented toward the front-left and front-right corners. All three communicate using I2C. During startup, the program initializes them separately and assigns each one its own I2C address so they can work together on the same bus.

The two diagonal ToF sensors help the robot understand the space near its front corners, while the frontal ToF sensor provides an additional measurement of the space directly in front of the vehicle.

Three ultrasonic **sonar sensors** are also used. One points forward, while the left and right sensors are mounted perpendicular to the sides of the vehicle. The side sonars are especially useful for detecting walls, corridors, and openings. The program continuously reads all three sonar sensors instead of taking only a single measurement when a decision needs to be made.

A **WonderCam AI Vision camera** is connected through I2C as part of the vehicle's hardware. The camera was included so that the project could later use visual information such as colors and objects. However, in the current Open Challenge program, the camera is prepared in the hardware but is not yet part of the main autonomous navigation loop.

Using different types of sensors was important because no single sensor can completely describe everything around the robot. For this reason, the vehicle combines information about distance, orientation, and movement before making decisions.

## Steering and Motors

The original **Geekservo steering mechanism** from the ELECFREAKS kit was kept.

The servomotor controls the front wheels. Instead of sending only left, center, or right commands, the program can send different steering values depending on how much the trajectory needs to be corrected.

The original DC motors from the building kit were also kept. These motors are controlled through a motor driver connected to the main ESP32.

The encoder is also used as motor feedback. This means that the program does not simply send power to the motors; it can also compare the requested speed with the movement measured by the encoder and adjust the motor output.

This became useful because the behavior of a real vehicle is never perfectly constant. Battery level, friction, weight, the floor surface, and the mechanical transmission can all affect the vehicle's actual speed.

## General Software Design

The MicroPython program was divided into different files instead of placing the entire robot operation inside one large program.

There are separate components for hardware configuration, sensors, actuators, navigation, perception, utilities, controller communication, and the robot's shared state.

One of the most important ideas in the program is the **shared state**.

The robot maintains one main structure containing the latest information from its sensors, its navigation mode, the commands that should be sent to the motor and steering servomotor, and the actual state of the actuators.

For example, the state contains information from the three sonar sensors, the three ToF sensors, the IMU, the encoder, and the camera. It also stores information such as the current navigation mode, current maneuver, reference *heading*, number of detected corners, and motor and steering commands.

This makes the software easier to understand because the different parts of the program communicate through the same robot state.

A sensor does not need to directly control a motor.

Instead, the sensor updates its information.

The navigation system reads that information and decides what should happen.

The actuator system then receives the requested movement and applies it to the real motor or servomotor.

In simple terms, the program works like this:

**Sensors → Robot State → Navigation Decision → Motor and Steering Commands**

## Reading All Components at the Same Time

An autonomous vehicle cannot stop the entire program every time it needs to read a sensor.

For this reason, the main ESP32 uses MicroPython's **uasyncio** system.

Different tasks run repeatedly for the IMU, sonar sensors, ToF sensors, encoder, buttons, PS4 controller, navigation system, motors, steering, and debugging.

These tasks are not truly separate programs running at exactly the same time; instead, they take turns very quickly.

This allows the robot to continue measuring its surroundings while it is moving.

For example, while the navigation system is deciding whether the next part of the track is a corner, another part of the program can continue updating the IMU, another can update the encoder, and another can continue reading the distance sensors.

## The State Machine

Autonomous navigation is organized as a **state machine**.

Instead of trying to solve the entire track using one very large set of conditions, the robot asks itself a simpler question:

**What am I doing right now?**

The program currently includes states such as:

* **Stopped**
* **Cruising**
* **Approaching**
* **Preparing a Turn**
* **Reversing Before a Turn**
* **Turning**
* **Exiting a Turn**
* **Failure / Safe State**

These states can be seen directly in the navigation program.

Each state has a specific purpose.

When the vehicle is in **Cruising**, its main objective is to move through the corridor while maintaining a suitable orientation and correcting its position.

When the frontal sensors begin to detect the end of the corridor, the vehicle switches to the **Approaching** state. It now moves more carefully and begins looking for the opening that will indicate the next corner.

The side sonar sensors are very important during this process because an opening on one side can indicate the direction of the next section of the track.

The diagonal ToF sensors can also detect changes near the corners of the vehicle and help the robot prepare for what is coming. In the current program, they can provide an early indication, but sonar information is used to confirm the direction before making the final turn decision.

If there is enough space, the robot begins the turn.

If it reaches the wall with too little space to perform the turn correctly, the state machine can first enter a short **reversing** maneuver. The encoder measures how far the vehicle has moved backward so that the robot does not reverse indefinitely.

During a normal 90-degree turn, the program changes its target *heading*. The IMU then allows the vehicle to compare its current orientation with the new direction it wants to reach.

Once the turn has been completed, the robot enters the exit phase of the maneuver and eventually returns to normal cruising.

The result is a repeating process:

**drive straight → detect corner → approach → decide direction → turn → find the new corridor → drive straight again**

This process continues as the robot travels around the track.

## Keeping the Vehicle Straight

Driving in a straight line is more difficult than simply placing the servomotor in its center position.

Small mechanical differences can cause the vehicle to slowly drift toward one of the walls.

For this reason, the program uses the **BMI160 heading** as an important reference.

When the vehicle enters a straight section, it has a desired direction. The current *heading* is compared with this reference, and the difference tells the program whether the robot is slowly drifting away from its intended direction.

The steering command can then correct this error.

The diagonal ToF sensors can also provide information about the vehicle's position relative to nearby walls. The difference between the left and right measurements can be converted into another small steering correction.

Instead of relying entirely on a single sensor, these corrections help the vehicle react to both its orientation and the nearby characteristics of the track.

## Manual Mode and PS4 Controller

Although the robot was designed for an autonomous competition, we also wanted it to be enjoyable and easy to test manually.

The second ESP32 provides this functionality.

It uses **Bluepad32** to connect to a compatible Bluetooth gamepad. The Arduino program reads information such as the steering joystick, buttons, directional pad, brake trigger, and throttle trigger.

This information is converted into a simple message and sent through UART to the MicroPython ESP32.

The MicroPython program receives these messages and separates them back into values representing the joystick, buttons, directional pad, and triggers.

When the robot is placed in **manual mode**, the controller can directly request steering and motor movement instead of allowing the autonomous state machine to make those decisions.

The triggers control forward and reverse movement, while the joystick can be used for steering.

Originally, this feature was added simply as a convenient way to drive the finished robot, but it became one of the most useful development tools.

The students could manually reproduce a corner, test the steering geometry, check motor behavior, position the vehicle at a specific location on the track, and compare a successful manual maneuver with the decisions made by the autonomous program.

## Debugging and Testing

A large part of the project was not simply writing code, but **testing the real vehicle**.

Values that looked correct on a computer did not always produce the expected result on the track.

For this reason, the students directly tested sensor distances, steering positions, motor speeds, turning angles, encoder readings, and IMU measurements on the vehicle.

The program also generates diagnostic information containing the readings from the front and side sensors, *heading*, target *heading*, current maneuver, motor speed, motor output, steering command, detected corners, and completed laps.

This information helped us understand what the robot believed was happening at each moment.

The Bluetooth controller was also extremely valuable during this process because it allowed us to compare two situations:

**What does a student do to successfully drive through this part of the track?**

and

**What does the autonomous program do in the same situation?**

This comparison helped us improve the autonomous decisions step by step.

## Development Process

The vehicle was developed gradually.

First, we built a mechanical vehicle that could move and steer.

Then, the original **micro:bit** electronics were replaced with the ESP32-based system.

After that, each sensor was tested separately.

Once the individual sensors were working correctly, their readings began to be stored in the robot's shared state.

The motor and steering systems were then separated from the navigation logic so that the navigation system could request a movement without needing to know every detail about how the motor or servomotor works.

Finally, the state machine was created and improved through repeated tests on the track.

The students used AI during this process as a programming assistant. Instead of asking AI to create the complete robot, individual problems were studied separately. Functions, ideas, and possible solutions generated with the help of AI were tested on the real hardware and then modified by the students when necessary.

This was important because a function that looks correct in theory does not necessarily work correctly on a physical robot. The final behavior depends on the real dimensions of the vehicle, sensor positions, motor response, steering system, track dimensions, and many other details that could only be understood through experimentation.

For this reason, the final robot is the result of many small cycles of:

**idea → programming → testing → observation → correction → testing again**

## Final Result

The final vehicle keeps the simple mechanical concept of the original ELECFREAKS steering model while replacing its electronics with a much more flexible ESP32-based system.

It can continuously read multiple sensors, maintain information about its current situation, choose actions through a state machine, control its steering and motor speed, recognize and perform turns, and switch to manual control using a Bluetooth gamepad.

Although it was created for **WRO Future Engineers**, it is still a small robotic vehicle built from educational components. Outside the competition, it can be driven using a controller, modified, used for experiments, and used as a learning platform for robotics, sensors, programming, control systems, and autonomous navigation.
