# Poker Application with Online play, Bots, and Kuhn Poker

[Overview](#project-overview)  
[UI Screenshots](#user-interface-screenshot)  
[Installation](#how-to-install)  
[Hosting Online Games](#how-to-host-a-game)  
[Joining Online Games](#how-to-join-an-online-game)  
[About Kuhn Poker](#kuhn-poker-1)  

## Project Overview

This project allows you to play poker against bots, friends or in a special game mode called Kuhn Poker. Most parts, such as the poker engine, GUI and the multi-player bots, were written in python. The training algorithm for the machine learning bot was written in rust - although rust is not needed to run the application

By selecting one device as the host, all devices on the same LAN can play with each other.

Alternatively, you can play against bots that use Minimum Defense Frequency (MDR) to construct hand ranges. After an action from any player, these bots will update their hand ranges. When it is their turn, they will  use these hand ranges to determine their action.

The final mode (Kuhn Poker) is a simplified 2 player version of poker. The bot in this mode uses Counterfactual Regret Minimisation (CFR) which is an iterative machine learning algorithm for solving imperfect information games such as poker. The bot trains across thousands of iterations by playing against itself and developing a 'regret' value each iteration. After each iteration, it updates its strategy to reduce this regret value.

## User Interface Screenshot

### Main Menu
<img width="3838" height="2106" alt="image" src="https://github.com/user-attachments/assets/62bf6c0e-e6d7-4e8c-b86e-685de2128a7e" />

### Texas Hold'em
<img width="3837" height="2107" alt="image" src="https://github.com/user-attachments/assets/e50d9376-61cb-4344-85e1-784eee6170df" />

<img width="3835" height="2108" alt="image" src="https://github.com/user-attachments/assets/16009d94-043f-4b9a-a794-8dbc2c7278b4" />

### Kuhn Poker
<img width="3838" height="2107" alt="image" src="https://github.com/user-attachments/assets/47f781ce-d9c4-4837-8a16-9bf3f6a56f96" />

## How to Install

1. Download python 3.12+ (earlier versions should work but 3.12 is what I started the project on) 
2. Clone the Repository or download and extract the zip file
3. Create a virtual environment by entering `python -m venv venv` into the terminal of the root (outmost) directory
4. Activate the virtual environment `source .venv/bin/activate` (Linux or macOS) or `./venv/Scripts/activate` (Windows). On windows, if you get an error, try entering `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first
5. Download dependencies with `pip install -r ./requirements.txt`
6. Navigate to the main_code directory `cd main_code`
7. Run the application! `python main.py`

## How to host a game

1. To find your private ipv4 ip address, in the terminal enter `ifconfig` (Windows), `ip addr show` (Linux) or `ipconfig getifaddr en0` (macOS)
2. Navigate to the main_code directory `cd main_code`
3. Start hosting the server `python server.py`

## How to join an online game
1. Go to the file main_code/main.py
2. Find line 59 (may change) with the code `def start_game(self, mode="Offline", host_ip=None):` you can do this easily by pressing ctrl f and typing host_ip
3. Change `None` to the host ip address so that line 59 is now `def start_game(self, mode="Offline", host_ip='171.35.61.2'):` where `171.35.61.2` the ip address of the host device
4. Run main.py as usual and click Play Online

NOTE: You must be on the same LAN as the host device to play
   
Alternatively, play an offline version on the [web app](https://jerryjmin.github.io/Poker/) (let it load and click ready to start)


## Kuhn Poker
### Rules

In the variation implemented in this project, the deck consists of one of each card from 2-A.

- Each player antes 1 chip
- Each player gets 1 card

On their turn, player can either pass or bet 1 chip. There is no raising

- If both players pass or both bet, showdown is reached where the player with the highest card wins.  
- If one player bets while the other passes, the player who bet wins.

#### Possible action sequences
- P1 passes → P2 passes: showdown.
- P1 passes → P2 bets → P1 passes: P2 wins.
- P1 passes → P2 bets → P1 bets: showdown.
- P1 bets → P2 passes: P1 wins.
- P1 bets → P2 bets: showdown.

### The Bot

The bot uses counterfactual regret minimisation (CFR). CFR simultaneously creates a strategy for both players at once by continuously playing and improving against itself over many training iterations. For every possible decision it could make, it generates a ‘regret’ value that represents what it would have gained had it taken that decision. It then uses this regret value to improve its current strategy. After thousands of iterations, the algorithm will improve its strategy until it reaches a Nash equilibrium – a situation where neither players' strategy can improve any further.

The bot you play against is incredibly accurate and despite the simplicity of the game, implements strategy that you would see in real poker such as bluffing. A perfect strategy against the bot in the application, which was trained with 500,000 training iterations, would win 0.0000457 chips per hand on average.

An in-depth project writeup can found here [Poker_Writeup.docx](https://github.com/user-attachments/files/29163596/Poker_Writeup.docx). The most interesting parts are within the design section
