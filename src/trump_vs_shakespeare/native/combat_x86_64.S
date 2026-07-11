.text

.globl tvs_next_random
.type tvs_next_random, @function
tvs_next_random:
    movq %rdi, %rax
    testq %rax, %rax
    jne .Lseed_ok
    movabsq $0x9E3779B97F4A7C15, %rax
.Lseed_ok:
    movq %rax, %rcx
    shrq $12, %rcx
    xorq %rcx, %rax
    movq %rax, %rcx
    shlq $25, %rcx
    xorq %rcx, %rax
    movq %rax, %rcx
    shrq $27, %rcx
    xorq %rcx, %rax
    movabsq $2685821657736338717, %rcx
    imulq %rcx, %rax
    ret
.size tvs_next_random, .-tvs_next_random

.globl tvs_hit
.type tvs_hit, @function
tvs_hit:
    xorl %eax, %eax
    cmpl %edi, %esi
    setl %al
    ret
.size tvs_hit, .-tvs_hit

.globl tvs_compute_damage
.type tvs_compute_damage, @function
tvs_compute_damage:
    testl %edi, %edi
    jle .Lzero
    movl %edx, %r9d
    movl %edx, %eax
    xorl %edx, %edx
    movl $21, %r8d
    divl %r8d
    addl $90, %edx
    movl %edi, %eax
    imull %edx, %eax
    cltd
    movl $100, %r8d
    idivl %r8d
    cmpl %ecx, %r9d
    jge .Lnot_crit
    leal (%rax,%rax,2), %eax
    cltd
    movl $2, %r8d
    idivl %r8d
.Lnot_crit:
    subl %esi, %eax
    cmpl $1, %eax
    jge .Ldone
    movl $1, %eax
.Ldone:
    ret
.Lzero:
    xorl %eax, %eax
    ret
.size tvs_compute_damage, .-tvs_compute_damage

.section .note.GNU-stack,"",@progbits
