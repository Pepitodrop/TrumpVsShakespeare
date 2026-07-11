.text

.global tvs_next_random
.type tvs_next_random, %function
tvs_next_random:
    mov x1, x0
    cbnz x1, 1f
    movz x1, #0x7c15
    movk x1, #0x7f4a, lsl #16
    movk x1, #0x79b9, lsl #32
    movk x1, #0x9e37, lsl #48
1:
    eor x1, x1, x1, lsr #12
    eor x1, x1, x1, lsl #25
    eor x1, x1, x1, lsr #27
    movz x2, #0xdd1d
    movk x2, #0x4f6c, lsl #16
    movk x2, #0xf491, lsl #32
    movk x2, #0x2545, lsl #48
    mul x0, x1, x2
    ret
.size tvs_next_random, .-tvs_next_random

.global tvs_hit
.type tvs_hit, %function
tvs_hit:
    cmp w1, w0
    cset w0, lt
    ret
.size tvs_hit, .-tvs_hit

.global tvs_compute_damage
.type tvs_compute_damage, %function
tvs_compute_damage:
    cmp w0, #0
    ble 2f
    mov w4, w2
    mov w5, #21
    udiv w6, w2, w5
    msub w6, w6, w5, w2
    add w6, w6, #90
    mul w0, w0, w6
    mov w5, #100
    sdiv w0, w0, w5
    cmp w4, w3
    bge 1f
    add w0, w0, w0, lsl #1
    asr w0, w0, #1
1:
    sub w0, w0, w1
    cmp w0, #1
    mov w5, #1
    csel w0, w0, w5, ge
    ret
2:
    mov w0, #0
    ret
.size tvs_compute_damage, .-tvs_compute_damage

.section .note.GNU-stack,"",@progbits
