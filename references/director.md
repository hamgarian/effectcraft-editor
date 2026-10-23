# Directing an original edit (no reference)

When there is no reference to match, decide the motion before any layout. An edit built scene by scene from
layouts plays like a slideshow: centred title, three items, cut, repeat.

## 1. One moving idea

Write one sentence before anything else:

> The edit moves by showing **[a thing that can move]** going from **[start state]** to **[end state]**, which shows **[the point]**.

The thing must be able to move as an object: a route on a map, a stack that grows, a signal passing between people,
a machine whose parts switch on, a crowd that gathers. If you can't name one, keep looking before planning shots.
For factual topics, check the claims first; keep facts short, they serve the motion.

## 2. Beat table

Plan a continuous timeline in a table. One row per beat:

| time | job (hook / reveal / contrast / mechanism / proof / close) | moving object | what changes on screen | camera or layer move | text (none / label / caption / title) | asset (generated, 3D set, shape, footage) | slideshow risk |
|---|---|---|---|---|---|---|---|

Rules:
- Every beat changes state. An entrance alone (fade, slide, pop) is not a change. If a beat only brings something in, add what happens to it next.
- Reuse 2-4 motion moves across the edit (a whip-cut, an on-twos push, a stamp-in, a curved path) and vary them. Don't use every effect.
- Text supports the picture. A beat that needs a paragraph read needs a different picture.
- Each scene gets its own world (environment, props, light). The camera carries continuity between them: whips, match cuts, a shared colour.
- Generated images only where they carry the story (a character, a place, an object), and plan how each one moves after it appears.

## 3. Slideshow check (before building, and again on the render)

Revise if any of these show up:
- a centred title with items under it, repeated
- a card on a plain background with no world around it
- cuts that reset everything, nothing carried across
- icons or images that appear and then sit still
- every element using the same fade and ease
- no camera move, matte, path, reveal or morph anywhere

Then review a frame grid of the render (`framestudy.py`, one frame every 0.5 s). It should read as a progression you
can follow without the captions. If it reads like six slide thumbnails, revise before the final render.
