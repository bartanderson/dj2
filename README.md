[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/bartanderson/dj2)

To start the system use 
"""python
run_game.py
"""

According to my AI chat.deepseek.com, The architecture in one sentence
Every interactive system (economy, encounter, combat, dialogue, quest) is a standalone FSM whose transitions are guarded and acted upon by shared, reusable game logic functions that read/write a context dictionary containing all relevant game state (character stats, enemy data, world flags, etc.).

That may sound simplistic but it was a long hard road to get here. Below are the beginnings of my heroes journey.

This is my long term attempt to create a DM AI for playing games by myself and or with friends so that we don't have to have a dungeon master on call to play when we want.
The idea is to create characters in a world/campaign that the DM creates and have it evolve with our decisions and there will be resulutions with consequences new quests and whatver comes next.
When its time for a new world the DM will create it and we will travel there. We may even travel back and forth. Who knows. I started with the dungeon generation that I took from donjon.
I tried a couple different versions but finally took the original perl script and translated it painstakingly to I believe js first and then finally python as that was where I wanted to be with my AI engine.
So got that working and tried to shoehorn in world and found out that was going to be a whole project. So started creating that then I had two systems. Now I have a runner that starts both.
I just got started integrating travel to the dungeon from a test location at the starting tavern location to get it done. Will be back to flesh out world travel and quests etc after that.
Then will get back to fleshing out the dungeon population and the NPC's in both ends and the monsters and quests and all the rest of a rich world.
I plan to add voice input and output if I can to give it a more interesting aspect, but that will be an optional add on. Working on the ai commands, which I first had workhing in the dungeon by the way.
Hope you enjoy this if you try to use it yourself. Lots left to do, I put in a lot of tools for analysis to help me because as big as this is getting I can't keep any major portion of it in my head.
But I can be the task master for the AI and beat it into submission to give me the changes I want often times. Lots of work and cleanup and todos left. There are guardrails which I use to keep the AI on track.
Bart
