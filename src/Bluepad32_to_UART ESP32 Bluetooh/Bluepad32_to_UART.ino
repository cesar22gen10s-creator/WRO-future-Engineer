#include <Arduino.h>
#include <Bluepad32.h>

ControllerPtr myControllers[BP32_MAX_GAMEPADS];

// UART2 -> GPIO16 RX2, GPIO17 TX2
HardwareSerial ControlUART(2);

static const int UART_RX_PIN = 16;
static const int UART_TX_PIN = 17;
static const uint32_t UART_BAUD = 115200;

// Ajusta esto si ves ruido en el centro del joystick
static const int JOYSTICK_DEADZONE = 25;

// =====================================================
// Estado que vamos a enviar a MicroPython
// Formato CSV:
// P,connected,lx,dpad,buttons,misc,brake,throttle
//
// Ejemplo centro:
// P,1,0,0,0,0,0,0
//
// Ejemplo izquierda:
// P,1,-511,0,0,0,0,0
// =====================================================
struct PadState {
  bool connected;
  int16_t lx;
  uint8_t dpad;
  uint16_t buttons;
  uint8_t misc;
  uint16_t brake;
  uint16_t throttle;
};

PadState lastSentState = {false, 0, 0, 0, 0, 0, 0};

// -----------------------------------------------------
// Utilidades
// -----------------------------------------------------
int16_t aplicarDeadzone(int value) {
  if (value > -JOYSTICK_DEADZONE && value < JOYSTICK_DEADZONE) {
    return 0;
  }
  return (int16_t)value;
}

bool sameState(const PadState& a, const PadState& b) {
  return a.connected == b.connected &&
         a.lx == b.lx &&
         a.dpad == b.dpad &&
         a.buttons == b.buttons &&
         a.misc == b.misc &&
         a.brake == b.brake &&
         a.throttle == b.throttle;
}

void enviarEstadoUART(const PadState& s) {
  ControlUART.print("P,");
  ControlUART.print(s.connected ? 1 : 0);
  ControlUART.print(",");
  ControlUART.print(s.lx);
  ControlUART.print(",");
  ControlUART.print(s.dpad);
  ControlUART.print(",");
  ControlUART.print(s.buttons);
  ControlUART.print(",");
  ControlUART.print(s.misc);
  ControlUART.print(",");
  ControlUART.print(s.brake);
  ControlUART.print(",");
  ControlUART.println(s.throttle);
}

// Busca el primer gamepad conectado
ControllerPtr obtenerGamepadActivo() {
  for (int i = 0; i < BP32_MAX_GAMEPADS; i++) {
    if (myControllers[i] && myControllers[i]->isConnected() && myControllers[i]->isGamepad()) {
      return myControllers[i];
    }
  }
  return nullptr;
}

PadState leerEstadoActual() {
  PadState s = {false, 0, 0, 0, 0, 0, 0};

  ControllerPtr ctl = obtenerGamepadActivo();
  if (!ctl) {
    return s;
  }

  s.connected = true;

  // Solo usamos el joystick izquierdo X para dirección
  s.lx = aplicarDeadzone(ctl->axisX());

  // Estos se mandan crudos para que Python decida
  s.dpad = (uint8_t)ctl->dpad();
  s.buttons = (uint16_t)ctl->buttons();
  s.misc = (uint8_t)ctl->miscButtons();
  s.brake = (uint16_t)ctl->brake();
  s.throttle = (uint16_t)ctl->throttle();

  return s;
}

// -----------------------------------------------------
// Callbacks Bluepad32
// -----------------------------------------------------
void onConnectedController(ControllerPtr ctl) {
  for (int i = 0; i < BP32_MAX_GAMEPADS; i++) {
    if (myControllers[i] == nullptr) {
      myControllers[i] = ctl;
      break;
    }
  }

  // Enviamos un estado inicial neutro/conectado
  PadState s = leerEstadoActual();
  enviarEstadoUART(s);
  lastSentState = s;
}

void onDisconnectedController(ControllerPtr ctl) {
  for (int i = 0; i < BP32_MAX_GAMEPADS; i++) {
    if (myControllers[i] == ctl) {
      myControllers[i] = nullptr;
      break;
    }
  }

  PadState s = {false, 0, 0, 0, 0, 0, 0};
  enviarEstadoUART(s);
  lastSentState = s;
}

// -----------------------------------------------------
// Setup / Loop
// -----------------------------------------------------
void setup() {
  // UART hacia la ESP32 con MicroPython
  ControlUART.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);

  // Inicializa Bluepad32
  BP32.setup(&onConnectedController, &onDisconnectedController);

  // OPCIONAL:
  // Si quieres borrar emparejamientos guardados en la ESP32 Arduino,
  // descomenta esta línea UNA sola vez, sube el sketch, prueba pairing,
  // y luego la vuelves a comentar.
  //
  // BP32.forgetBluetoothKeys();

  // Si en tu versión existe y quieres bloquear mouse virtual/touchpad:
  // BP32.enableVirtualDevice(false);
}

void loop() {
  // Actualiza datos del mando
  BP32.update();

  // Lee estado actual
  PadState current = leerEstadoActual();

  // Solo manda si hubo cambio real
  if (!sameState(current, lastSentState)) {
    enviarEstadoUART(current);
    lastSentState = current;
  }

  delay(10);
}