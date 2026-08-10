/*
 * coop_blink.c — cooperative-scheduler blink on ATmega328P.
 *
 * Two scripts (tasks) sharing a 1 ms Timer0 tick:
 *   task0: toggle D13 (LED) every 500 ms
 *   task1: toggle D12 every 200 ms
 *
 * Same Duff's-device pattern as the STC12 target.
 */

#include "avr_runtime.h"

/* ---- task state ---- */

static uint16_t bw_task0_state;
static uint32_t bw_task0_until;

static void bw_task0(void)
{
    switch (bw_task0_state) {
    case 0:
    bw_task0_state = 1;
    case 1:
    bw_pin_toggle(13);   /* D13 */
    bw_task0_until = bw_now() + 500;
    bw_task0_state = 2;
    case 2:
    if ((int32_t)(bw_now() - bw_task0_until) < 0) return;
    bw_task0_state = 1;
    return;
    }
    bw_task0_state = 0xFFFF;
}

static uint16_t bw_task1_state;
static uint32_t bw_task1_until;

static void bw_task1(void)
{
    switch (bw_task1_state) {
    case 0:
    bw_task1_state = 1;
    case 1:
    bw_pin_toggle(12);   /* D12 */
    bw_task1_until = bw_now() + 200;
    bw_task1_state = 2;
    case 2:
    if ((int32_t)(bw_now() - bw_task1_until) < 0) return;
    bw_task1_state = 1;
    return;
    }
    bw_task1_state = 0xFFFF;
}

int main(void)
{
    bw_pin_output(13);
    bw_pin_output(12);
    bw_setup_timer();
    sei();

    for (;;) {
        bw_task0();
        bw_task1();
    }
}
