## Art

### Playscii

I used a forked version of the playscii ASCII art program to generate the ``.psci`` files:

https://github.com/michael-lazar/playscii

Botany's original plaintext art files were imported using the following settings:

- palette: ``240-ansi`` (generated using [this script](art/scripts/build_palette.py))
- charset: ``dos`` (of which 7-bit US ASCII is a subset)

I intentionally excluded colors 0-15 from the palette because those colors can
be modified by a user's terminal theme, and I wanted total control of the
final rendered text. One could argue that I should *only* be using colors 0-15
for that reason. I wanted to try something different.

When colorizing, I maintained a few common colors between plants:

| Color Code | Usage |
| --- | --- |
| 0 | background |
| 80 | soil |
| 133 | primary flower color |
| 199 | secondary flower color |

Some plants also contained other colors:

1. poppy (92 green)
2. cactus (8 green, 37 pot, 14 spike)
3. aloe (20 green)
4. venus flytrap (104 green, 152 pink)
5. jade plant (56 green, 79 trunk)
6. fern (19 green)
7. daffodil (14 green)
8. sunflower (13 green, 37 brown)
9. baobab (13 green, 158 trunk)
10. lithops (55 green, 118 body)
11. hemp (20 green)
12. pansy (19 green)
13. iris (62 green)
14. agave (14 green, 73 tip, 122 stalk)
15. ficus (61 green, 94 trunk)
16. moss (13 green, 230 stone)
17. sage (20 green)
18. snapdragon (61 green, 139 bud)
19. columbine (55 green)
20. brugmansia (62 green)
21. palm (13 green, 85 trunk)
22. pachypodium (56 green, 86 trunk)
23. seed (200 seed)
24. seedling (18 green)
25. rip (19 grass, 228 tombstone)
