---
title: Water runs downhill
date: 2026-10-24
author: Yasno Games
summary: The evening our last post went up, we deleted the rivers. Twelve days later they wind down their valleys. Here is what they did in between.
image: river.jpg
---
![A blue river winding along the floor of a forested valley, seen from the slope above](river.jpg)

Our last post ended with "the rivers went in this month." That evening we
deleted them: four layers of the world generator, 4,295 lines of code. The
river above replaced them. It runs about five kilometres from where a new
player starts.

The old rivers were routed between points 525 tiles apart. The generator
knew the ground's height at those points and assumed a straight line between
them, so wherever a ridge stood between two points, the river ran over it.
In one stretch of the world we counted 20 places where a river climbed 16
metres or more. Every patch we made moved the climbs somewhere else.

The new generator builds the ground on hex cells of seven sizes, each three
times finer than the one above, from cells 729 tiles across down to single
tiles. Water is routed at every size. A river found among the big cells is
handed down to the next size, which lays it over its own finer ground and
finds smaller rivers there.

![Water hanging in the air as a staircase of blocks up a rocky mountainside](floating.jpg)

In its first days in the game the new water stood in the air, a staircase of
blocks up the side of a mountain.

![A plain below a slope, cut by a row of straight parallel streams like the teeth of a comb](comb.jpg)

Then the rivers ran straight. Each size hands its ground down to the next as
flat sloping triangles, and every stream on a flat slope takes the same
steepest way down. A slope full of streams came out as a comb.

![A world under water: translucent blue walls and sheets standing over cliffs and hills](drowned.jpg)

That is October 15, mid-afternoon.

What straightened out the comb was handing a river down whole. A level now
passes each river's course to the next size, which bends it through the
ground beside it, so a river picks up bends at every size. A stream that
starts on a plain wanders toward whatever lies lower around it, so streams
gather into trunks.

![The world viewer's render of a valley: one dead-straight river with straight tributaries joining it at angles](straight.jpg)

![The same valley in the world viewer: the river winds down the valley floor, its banks curving with it](winding.jpg)

Those two are the same valley in our world viewer, which draws the
generator's tiles without the game's look: on October 22, then today.

![A broad lake that ends in a straight wall of water standing above the grass, in the rain](lake-wall.jpg)

Lakes still go wrong. That one, yesterday morning, ends in a straight wall
of water.

![A stream with small ponds along it at the bottom of a wooded valley](ponds.jpg)

When they work, a stream runs down a wooded valley and fills a few ponds on
the way.

The rivers come from a generator: seeded code, no trained model, nothing
drawn by hand. Claude writes that code with us, and we decide what a river
should look like and throw out what isn't one.
