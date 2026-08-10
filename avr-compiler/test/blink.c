/* Bare-AVR blink — no Arduino libraries.
 * DDRB/PORTB toggle with a _delay loop.
 * Target: ATmega328P, 16 MHz assumed. */

#include <avr/io.h>
#include <util/delay.h>

#define F_CPU 16000000UL

int main(void)
{
    DDRB |= (1 << PB5);        /* pin 13 (LED) as output */

    for (;;) {
        PORTB |= (1 << PB5);   /* LED on */
        _delay_ms(500);
        PORTB &= ~(1 << PB5);  /* LED off */
        _delay_ms(500);
    }
}
