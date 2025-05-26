#ifndef DEBUG_H
#define DEBUG_H

#include <Arduino.h>

// Set this to 1 to enable verbose debug output
#define DEBUG_MODE 1

#if DEBUG_MODE
  #define DEBUG_PRINT(x) Serial.print(x)
  #define DEBUG_PRINTLN(x) Serial.println(x)
  #define DEBUG_PRINTFMT(x, y) Serial.print(x, y)
  #define DEBUG_PRINTF(format, ...) Serial.printf(format, __VA_ARGS__)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
  #define DEBUG_PRINTFMT(x, y)
  #define DEBUG_PRINTF(format, ...)
#endif

class DebugTimer {
private:
  unsigned long startTime;
  String operationName;

public:
  DebugTimer(String name) : operationName(name) {
    startTime = millis();
  }

  ~DebugTimer() {
    unsigned long duration = millis() - startTime;
    #if DEBUG_MODE
      Serial.print("[TIMING] ");
      Serial.print(operationName);
      Serial.print(": ");
      Serial.print(duration);
      Serial.println(" ms");
    #endif
  }
};

#endif // DEBUG_H
