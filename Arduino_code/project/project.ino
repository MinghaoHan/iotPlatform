#include <Arduino_FreeRTOS.h>
#include <queue.h>
#include <DHT.h>
#define DHTPIN 8
#define DHTTYPE DHT11
#define buzzPin 12
#define ledPin 13

int mode = 0;
int gotRes = 0;

QueueHandle_t xQueue, xQueue1;

void setup() {
  xQueue = xQueueCreate( 2, sizeof( byte ) );
  xQueue1 = xQueueCreate( 1, sizeof( byte ) );
  
  if ( xQueue != NULL)
  {
    xTaskCreate( ReadHT, "HT handler", 380, NULL, 1, NULL );
    xTaskCreate( Printer, "Serial Printer", 380, NULL, 3, NULL );
  }
  if (xQueue1 != NULL) {
    xTaskCreate( Buzzer, "Alert", 120, NULL, 2, NULL );
    vTaskStartScheduler();
  }
}

void loop() {
  if ((mode & 1) >= 1) {
    digitalWrite(ledPin, HIGH);
  }
  if ((mode & 2) >= 1) {
    digitalWrite(ledPin, HIGH);
    delay( 100 );
    digitalWrite(ledPin, LOW);
    delay( 100 );
  }
  if ((mode & 3) == 0) {
    digitalWrite(ledPin, LOW);
  }
  if ((mode & 4) >= 1) {
    digitalWrite(buzzPin, LOW);
    delay( 100 );
    digitalWrite(buzzPin, HIGH);
    delay( 100 );
  }
  if ((mode & 4) == 0) {
    digitalWrite(buzzPin, HIGH);
  }
}

void ReadHT( void *pvParameters ) {
  (void) pvParameters;

  DHT dht(DHTPIN, DHTTYPE);
  dht.begin();

  for ( ;; )
  {
    vTaskDelay( 1000 / portTICK_PERIOD_MS );

    byte temperature;
    temperature = (byte)dht.readTemperature();

    if (!isnan(temperature)) {
      xQueueSend( xQueue, &temperature, portMAX_DELAY );
      taskYIELD();
    }
  }
}

void Printer( void *pvParameters ) {
  (void) pvParameters;

  Serial.begin(9600);

  while (!Serial) {
    vTaskDelay(1);
  }
 
  for ( ;; )
  {
    byte temperature;
    byte res;
    
    if (xQueueReceive( xQueue, &temperature, portMAX_DELAY ) == pdPASS)
    {
      Serial.println(temperature);
    }

    for (int i = 0; i < 2; i++) {
      if (Serial.available() > 0) {
        res = Serial.read();
        Serial.read();
        if (xQueueSend( xQueue, &res, (TickType_t) 10 ) != pdPASS ) {
          Serial.println("F");
          Serial.read();
          Serial.read();
        }
        if (i == 1) {
          gotRes = 1;
        }
      }
    }
    vTaskDelay( 1000 / portTICK_PERIOD_MS );
    taskYIELD();
  }
}

void Buzzer( void *pvParameters ) {
  (void) pvParameters;

  pinMode(ledPin, OUTPUT);   //定义引脚模式为输出模式
  digitalWrite(ledPin, LOW);
  
  pinMode(buzzPin, OUTPUT);   //定义引脚模式为输出模式
  digitalWrite(buzzPin, HIGH);      //输入高电平（静音）

  for ( ;; )
  {
    vTaskDelay( 1000 / portTICK_PERIOD_MS );
    
    byte flag;
    for (int i = 0; i < 2; i++) {
      if (gotRes == 1 && xQueueReceive( xQueue, &flag, (TickType_t) 10 ) == pdPASS)
      {
        int cur = flag - (byte)'0';
  
        if (cur == 6) {       // known face, light on
          mode = mode & ~2;
          mode = mode | 1;
        }
        else if (cur == 4) {  // unknown face, blink
          mode = mode & ~1;
          mode = mode | 2;
        }
        else if (cur == 5) {  // no face, no light
          mode = mode & ~3;
        }
        else if (cur == 1) {  // temp high, tick
          mode = mode | 4;
        }
        else if (cur == 0) {  // temp normal, no buzz
          mode = mode & 3;
        }

        if (i == 1) {
          gotRes = 0;
        }
      }
    }
    taskYIELD();
  }
}
