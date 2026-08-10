/*
 * avr_runtime.h — cooperative scheduler for BrickWright on ATmega328P.
 *
 * The same pattern as the STC12 target: Timer0 at 1 ms tick, each WHEN
 * script is a Duff's-device state machine that yields at every wait and
 * loop back-edge. Scratch's own scheduling contract.
 *
 * F_CPU must be defined before including this (the compile endpoint does it).
 */

#ifndef AVR_RUNTIME_H
#define AVR_RUNTIME_H

#include <avr/io.h>
#include <avr/interrupt.h>
#include <stdint.h>

/* ---- millisecond tick via Timer0 ---- */

static volatile uint32_t bw_ms;

ISR(TIMER0_COMPA_vect)
{
    bw_ms++;
}

static uint32_t bw_now(void)
{
    uint32_t t;
    cli();
    t = bw_ms;
    sei();
    return t;
}

static void bw_setup_timer(void)
{
    /* Timer0 in CTC mode, prescaler /64, compare match at 1 ms.
     * At F_CPU = 16 MHz: 16e6 / 64 = 250 kHz → 250 counts per ms.
     * OCR0A = 249 (count 0..249 = 250 ticks). */
    TCCR0A = (1 << WGM01);                /* CTC mode */
    TCCR0B = (1 << CS01) | (1 << CS00);   /* prescaler /64 */
    OCR0A  = (uint8_t)((F_CPU / 64 / 1000) - 1);
    TIMSK0 = (1 << OCIE0A);               /* compare-match interrupt */
}

/* ---- delay (blocking, for single-script or custom blocks) ---- */

static void delay_ms(uint16_t ms)
{
    uint32_t start = bw_now();
    while ((int32_t)(bw_now() - start) < (int32_t)ms)
        ;
}

/* ---- pin helpers ---- */

/* Arduino pin number → DDR/PORT/PIN register + bit mask.
 * Uno/Nano only: D0–D13, A0–A5 (= D14–D19). */

typedef struct {
    volatile uint8_t *ddr;
    volatile uint8_t *port;
    volatile uint8_t *pin;
    uint8_t mask;
} bw_pin_t;

static const bw_pin_t BW_PINS[] = {
    /* D0  */ { &DDRD, &PORTD, &PIND, 1 << 0 },
    /* D1  */ { &DDRD, &PORTD, &PIND, 1 << 1 },
    /* D2  */ { &DDRD, &PORTD, &PIND, 1 << 2 },
    /* D3  */ { &DDRD, &PORTD, &PIND, 1 << 3 },
    /* D4  */ { &DDRD, &PORTD, &PIND, 1 << 4 },
    /* D5  */ { &DDRD, &PORTD, &PIND, 1 << 5 },
    /* D6  */ { &DDRD, &PORTD, &PIND, 1 << 6 },
    /* D7  */ { &DDRD, &PORTD, &PIND, 1 << 7 },
    /* D8  */ { &DDRB, &PORTB, &PINB, 1 << 0 },
    /* D9  */ { &DDRB, &PORTB, &PINB, 1 << 1 },
    /* D10 */ { &DDRB, &PORTB, &PINB, 1 << 2 },
    /* D11 */ { &DDRB, &PORTB, &PINB, 1 << 3 },
    /* D12 */ { &DDRB, &PORTB, &PINB, 1 << 4 },
    /* D13 */ { &DDRB, &PORTB, &PINB, 1 << 5 },
    /* A0  */ { &DDRC, &PORTC, &PINC, 1 << 0 },
    /* A1  */ { &DDRC, &PORTC, &PINC, 1 << 1 },
    /* A2  */ { &DDRC, &PORTC, &PINC, 1 << 2 },
    /* A3  */ { &DDRC, &PORTC, &PINC, 1 << 3 },
    /* A4  */ { &DDRC, &PORTC, &PINC, 1 << 4 },
    /* A5  */ { &DDRC, &PORTC, &PINC, 1 << 5 },
};

static inline void bw_pin_output(uint8_t pin)
{
    *BW_PINS[pin].ddr |= BW_PINS[pin].mask;
}

static inline void bw_pin_input(uint8_t pin)
{
    *BW_PINS[pin].ddr &= ~BW_PINS[pin].mask;
}

static inline void bw_pin_high(uint8_t pin)
{
    *BW_PINS[pin].port |= BW_PINS[pin].mask;
}

static inline void bw_pin_low(uint8_t pin)
{
    *BW_PINS[pin].port &= ~BW_PINS[pin].mask;
}

static inline void bw_pin_toggle(uint8_t pin)
{
    *BW_PINS[pin].port ^= BW_PINS[pin].mask;
}

static inline uint8_t bw_pin_read(uint8_t pin)
{
    return (*BW_PINS[pin].pin & BW_PINS[pin].mask) ? 1 : 0;
}

/* ---- ADC (10-bit, channels 0–5 = A0–A5) ---- */

static uint16_t bw_adc_read(uint8_t channel)
{
    ADMUX  = (1 << REFS0) | (channel & 0x07);   /* AVCC ref, channel */
    ADCSRA = (1 << ADEN) | (1 << ADSC)           /* enable + start */
           | (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);  /* /128 prescaler */
    while (ADCSRA & (1 << ADSC))
        ;
    return ADC;
}

#endif /* AVR_RUNTIME_H */
