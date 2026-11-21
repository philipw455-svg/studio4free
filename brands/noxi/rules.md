# Noxi: rules

Hard rules. Every video must pass all of them. Source: Philip's build prompt (2026-11-14) unless a line says otherwise.
The brain check tests the rules marked (checked). Claude checks the rest by eye on the storyboard and on the rendered frames.

1. Open with a desire hook. The first line says what the viewer wants, not what is wrong.
2. One line per frame. Each line stays on screen about 2 seconds. (checked: under 2 seconds, and more than one line)
3. No drinks, no drink words and no drink emoji. (checked: the avoid list in `voice.md`)
   Also from Apple guideline 1.4.3 and the Noxi repo `CLAUDE.md`: never encourage drinking.
4. No real faces from the app. Mascots, drawn people or generated people only.
   App screenshots use made-up names and placeholder pictures, never a real account's photo (Philip, Noxi website rules).
5. Keep all words inside the Reels safe area: not in the top 240 px, the bottom 440 px or the right 190 px of a 1080 x 1920 frame.
   (checked when a frame gives `box`)
6. Clock times in numbers. Never Roman numerals for clock times. (checked)
7. One feature per video. Never a feature list.
8. Every claim must match `facts.md`. (checked)
9. Users are 18 and older. Never show or suggest anyone younger. (Noxi repo `CLAUDE.md`)
10. No pure white and no pure black in Noxi art. (Philip, app rules)
11. Never show a retired kit item. (checked: `kit.md`)

## Claim words
A line that uses one of these words, or any number, makes a claim. The brain check looks for a fact in `facts.md` whose keys cover it.
- free, paid, price, 18+, iphone, android, app store, google play, delete, deletes, deleted, gone, private, launch, launches, only, never, always, safe, secure, encrypted, unlimited, best, first, new, everyone board, state feed, your state, every crew, friends, looks, recap, xp
