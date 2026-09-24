/* mutation.c - THE MUTATION LAW.  GENERATED; every lane authored by search.
 *
 * Which candidate line to examine first, ranked by WHAT HAPPENS WHEN IT IS
 * CHANGED.  Decided for ONE line, from eight measured facts and nothing else.
 *
 *   mutation(x) -> 0..15   higher = examine first
 *                          0 = no mutant of this line touched the failure
 *
 * ============ WHY THIS IS NOT MORE CIRCUMSTANTIAL EVIDENCE ============
 *
 * The CAUSE law ranks lines by eight bits of circumstance, and on real bugs
 * that is usually ONE bit - EF_ALL - with the spectrum tie-break doing the
 * ordering.  On the five longest-lived real bugs the guilty line sat at rank
 * 28, 11, 20, 32; in a 2,000-line file of coverage-identical lines it sat at
 * 218 inside a band of 84 the law could not tell apart.  COVERAGE SAYS WHICH
 * LINES WERE THERE.  IT CANNOT SAY WHICH LINE MATTERS.
 *
 * These bits are an EXPERIMENT on the line, not an observation of it.  The
 * body alters the line one operator at a time and runs the failing tests and
 * the passing tests that execute it - never the whole suite.  A mutant that
 * turns the failing test green is a line whose CONTENT the outcome depends
 * on.  A mutant that turns the whole set green is a repair candidate.
 *
 *   bit 0 FLIP     some mutant turns the JUDGED failing test green
 *   bit 1 ALL      some single mutant turns EVERY failing test green
 *   bit 2 CLEAN    some single mutant turns every failing test green and no
 *                  covering passing test red - a repair candidate
 *   bit 3 EDIT     a flipping mutant is an EDIT, not a deletion
 *   bit 4 MOVES    some mutant CHANGES the failure - different value,
 *                  exception or line - without turning it green
 *   bit 5 UNIQUE   this is the ONLY line in the pool with FLIP
 *   bit 6 BREAKS   EVERY mutant that ran turned some covering passing test
 *                  red - the line is load-bearing and no edit of it helped
 *   bit 7 SILENT   every mutant that ran changed nothing anywhere
 *
 * NO NUMBER HERE IS A WEIGHT.  The four lanes are COUNTED, not weighted:
 * s strong and w weak, and the priority is the dense lexicographic rank of
 * (s, w).  One strong beats any number of weak because the rank says so.
 *
 *   REPAIR  strong CLEAN              weak ALL without CLEAN
 *   FLIP    strong FLIP and UNIQUE    weak FLIP
 *   KIND    strong EDIT               -
 *   FLOW    -                         weak MOVES
 *
 * A DELETION MUST NOT OUTRANK AN EDIT, and the grades are what enforce it,
 * not the kernel: deleting a guard can make an assertion pass by skipping
 * the check that was asserting, so KIND is strong only on an EDIT and a
 * deletion-only line carries no KIND grade at all.
 *
 * BREAKS IS NOT A LANE, IT IS THE REGIME, AND IT IS A SHIFT.  A line whose
 * every alteration breaks correct behaviour is more likely correct code the
 * failing path merely runs through, so its priority is halved.  Halving is a
 * shift by one and BREAKS is already 0 or 1, so the regime IS the shift
 * amount - cleaner than the omission law's (1 - RAISED).  A faulty line can
 * also be load-bearing, so BREAKS shifts and never vetoes.
 *
 * SILENT IS NOT A LANE EITHER.  It lets the body distinguish "measured and
 * nothing" from "not measured"; to the law both are R0.  A line whose
 * mutants the budget cut is unmeasured, all bits 0, and vetoed - SILENCE IS
 * NOT INNOCENCE.
 *
 * RANK 15 IS UNREACHABLE (R4), and the reason is structural: KIND has no
 * weak grade and FLOW no strong one, so at most three lanes can be strong
 * and the top attainable rank is 14 at (3,1).  The CAUSE law loses 5 and the
 * OMISSION law loses 15 for the same reason - a one-sided lane truncates an
 * end of the dense rank.  Measured here, not assumed.
 *
 * RUN IT BESIDE THE OTHER TWO, NEVER BLENDED.  "Which line did the failing
 * test run", "where does missing code belong" and "which line's content does
 * the outcome depend on" are different questions with different regimes.
 *
 * 45 of the 256 words are reachable; the rest were never posed and the check
 * below confirms the law still lands in 0..15 on them.
 *
 * What this law does NOT decide: whether it beats coverage on real bugs.
 * That is the 2,000-line case moving from 218 to the top, the five
 * long-lived bugs, and the held-out rich and click halves - and if the table
 * is wrong it changes by a stated principle before a new kernel is asked for.
 */
#include <stdio.h>
#include <stdint.h>

static inline int32_t L_FLIP   (int32_t x) { return (x & 1); }
static inline int32_t L_ALL    (int32_t x) { return (1 & (x >> 1)); }
static inline int32_t L_CLEAN  (int32_t x) { return (1 & (x >> 2)); }
static inline int32_t L_EDIT   (int32_t x) { return (1 & (x >> 3)); }
static inline int32_t L_MOVES  (int32_t x) { return (1 & (x >> 4)); }
static inline int32_t L_UNIQUE (int32_t x) { return (1 & (x >> 5)); }
static inline int32_t L_BREAKS (int32_t x) { return (1 & (x >> 6)); }
static inline int32_t L_SILENT (int32_t x) { return (x >> 7); }
static inline int32_t L_F      (int32_t x) { return ((x - (x >> 1)) + (x | (x + x))); }

static inline int32_t KEEP  (int32_t x)     /* R0: a mutant touched the failure */
{ return L_FLIP(x) | L_MOVES(x); }
/* CLEAN => ALL => FLIP and UNIQUE => FLIP, so the strong terms need no AND */
static inline int32_t STRONG(int32_t x)
{ return L_CLEAN(x) + L_UNIQUE(x) + L_EDIT(x); }
static inline int32_t NONSIL(int32_t x)
{ return L_ALL(x) + L_FLIP(x) + L_EDIT(x) + L_MOVES(x); }

int32_t mutation(int32_t x)
{ return ((0 - KEEP(x))
        & ((1 + NONSIL(x) + L_F(STRONG(x))) >> L_BREAKS(x))) & 15; }

/* ===== INDEPENDENT ORACLE: branchy, shares no expression with a lane ==== */
static const int BASE[5] = {0, 5, 9, 12, 14};
static int oracle(int x)
{   int fl=(x>>0)&1, al=(x>>1)&1, cl=(x>>2)&1, ed=(x>>3)&1;
    int mv=(x>>4)&1, uq=(x>>5)&1, br=(x>>6)&1;
    int rep, flp, knd, flw, s = 0, w = 0, r;
    if (!fl && !mv) return 0;                                /* R0 */
    if (cl) rep = 2; else if (al) rep = 1; else rep = 0;
    if (fl && uq) flp = 2; else if (fl) flp = 1; else flp = 0;
    if (ed) knd = 2; else knd = 0;
    if (mv) flw = 1; else flw = 0;
    if (rep==2) s++; else if (rep==1) w++;
    if (flp==2) s++; else if (flp==1) w++;
    if (knd==2) s++; else if (knd==1) w++;
    if (flw==2) s++; else if (flw==1) w++;
    r = 1 + BASE[s] + w;
    if (br) return r >> 1; else return r; }
static int reach(int x)
{   int fl=(x>>0)&1, al=(x>>1)&1, cl=(x>>2)&1, ed=(x>>3)&1;
    int mv=(x>>4)&1, uq=(x>>5)&1, br=(x>>6)&1, si=(x>>7)&1;
    if (cl && !al) return 0;
    if (al && !fl) return 0;
    if (ed && !fl) return 0;
    if (uq && !fl) return 0;
    if (si && (fl || mv || br)) return 0;
    if (cl && br) return 0;
    return 1; }
static int s_of(int x)
{   int fl=(x>>0)&1, cl=(x>>2)&1, ed=(x>>3)&1, uq=(x>>5)&1;
    return cl + (fl && uq) + ed; }
static int w_of(int x)
{   int fl=(x>>0)&1, al=(x>>1)&1, cl=(x>>2)&1, mv=(x>>4)&1, uq=(x>>5)&1;
    return (al && !cl) + (fl && !uq) + mv; }

int main(void)
{
    long tab=0,r0=0,r1=0,r2=0,r3=0,r4=0,rng=0,anc=0,nre=0,smax=0;
    int x,y,i;
    for (x=0;x<256;x++) if (reach(x)) { nre++;
        if (mutation(x)!=oracle(x)) tab++;
        if (s_of(x)>smax) smax=s_of(x); }
    printf("  reachable words                            %ld  (want 45)\n", nre);
    printf("  against the table, all 45 reachable        %ld\n", tab);
    for (x=0;x<256;x++) if (reach(x))
        if (!((x>>0)&1) && !((x>>4)&1) && mutation(x)!=0) r0++;
    printf("  R0 neither FLIP nor MOVES -> 0             %ld\n", r0);
    /* R1 and R3 hold WITHIN a regime: BREAKS scales the whole ruling. */
    for (x=0;x<256;x++) if (reach(x) && mutation(x))
      for (y=0;y<256;y++) if (reach(y) && mutation(y)
                             && (((x>>6)&1)==((y>>6)&1))) {
        int sx=s_of(x), wx=w_of(x), sy2=s_of(y), wy2=w_of(y);
        if (sx>sy2 && !(mutation(x)>=mutation(y))) r1++;
        if (sx==sy2 && wx>wy2 && !(mutation(x)>=mutation(y))) r1++;
        if (sx==sy2 && wx==wy2 && mutation(x)!=mutation(y)) r3++; }
    printf("  R1 one strong beats any number of weak     %ld\n", r1);
    printf("  R3 only the counts matter, no lane wins    %ld\n", r3);
    for (x=0;x<256;x++) if (reach(x))
        for (i=0;i<8;i++) { if (i==6) continue;
            if (!(x&(1<<i)) && reach(x|(1<<i))
                && mutation(x|(1<<i)) < mutation(x)) r2++; }
    printf("  R2 monotone, BREAKS excepted               %ld\n", r2);
    if (smax!=3) r4++;
    for (x=0;x<256;x++) if (reach(x) && mutation(x)==15) r4++;
    printf("  R4 max strong = %ld, so rank 15 unreachable %ld\n", smax, r4);
    /* a deletion must not outrank an edit: same bits, EDIT off vs on */
    {   long del=0;
        for (x=0;x<256;x++) if (reach(x) && !((x>>3)&1) && reach(x|8))
            if (mutation(x) > mutation(x|8)) del++;
        printf("  a deletion never outranks the same edit    %ld\n", del);
        r2 += del; }
    /* SILENT appears in NO lane of the kernel.  That is the spec's claim -
       "to the law both are R0" - and the compiler caught it as an unused
       function, so it is proved here rather than suppressed: every reachable
       SILENT word must rule 0, by way of the veto and nothing else. */
    {   long sil=0, used=0;
        for (x=0;x<256;x++) if (reach(x) && L_SILENT(x)) { used++;
            if (mutation(x)!=0) sil++; }
        printf("  SILENT is in no lane; all %ld such words rule 0  %ld\n",
               used, sil);
        r0 += sil; }
    for (x=0;x<256;x++) { int a=mutation(x); if (a<0||a>15) rng++; }
    printf("  total on 0..255, lands in 0..15            %ld\n", rng);
    {   const int AX[7]={15,63,41,16,65,64,128};
        const int AW[7]={11,14,10, 2, 1, 0,  0};
        const char *AN[7]={
          "FLIP+ALL+CLEAN+EDIT  mealie credentials_provider",
          "the same plus UNIQUE the 2,000-line file",
          "FLIP+EDIT+UNIQUE     two failing causes",
          "MOVES alone          wrong value, no fix",
          "FLIP+BREAKS          deletion only, halved",
          "BREAKS alone         a shared helper",
          "SILENT               a logging line"};
        printf("\n  THE ANCHORS\n");
        for (i=0;i<7;i++) { int a=mutation(AX[i]);
            if (a!=AW[i]) anc++;
            printf("    x=%-4d %-46s -> %2d  (want %2d)\n",
                   AX[i], AN[i], a, AW[i]); } }
    printf("\n  TOTAL  %ld violations\n",
           tab+r0+r1+r2+r3+r4+rng+anc+(nre!=45));
    return (tab+r0+r1+r2+r3+r4+rng+anc+(nre!=45)) != 0;
}
