
import './App.css';
// MUI imports
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
// import { Typography } from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

// Image imports
import ivyLogoAssassin from './ivy_logo_assassin.png';

// React imports
import React, { useState, useEffect } from 'react';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});


// TODO: Deploy to render, make list optimized for mobile and look cooler (with avatars)

function App() {
  const API_URL = 'https://assassin-api.onrender.com';
  const gameName = 'test_game';
  const [playerInfo, setPlayerInfo] = useState([]);

  useEffect(() => {
    fetch(`${API_URL}/api/game-stats/${gameName}`)
      .then(response => response.json())
      .then(game_stats => {
        const playerIds = Object.keys(game_stats);
        Promise.all(playerIds.map(netid => fetch(`${API_URL}/api/players/${netid}`))).then(data => console.log(data))
          .then(responses => Promise.all(responses.map(response => response.json())))
          .then(players => {
            const updatedPlayerInfo = playerIds.map(netid => {
              const playerKills = game_stats[netid]["kills"];
              const playerIsAlive = game_stats[netid]["isAlive"];
              const playerInfo = players.find(player => player.netid === netid);
              return {
                netid,
                name: playerInfo.name,
                nickname: playerInfo.nickname,
                kills: playerKills,
                isAlive: playerIsAlive
              };
            });
            setPlayerInfo(updatedPlayerInfo);
          });
      });
  }, []);


  const [message, setMessage] = useState('');
  useEffect(() => {
    fetch(`${API_URL}/hello_world`)
      .then(response => response.text())
      .then(data => setMessage(data));
  }, []);

  // const playerInfo = [
  //   { playerId: "jsmith", name: "John Smith", nickname: "The Hammer", kills: 2 },
  //   { playerId: "jdoe", name: "Jane Doe", nickname: "The Assassin", kills: 4 },
  //   { playerId: "bjohnson", name: "Bob Johnson", nickname: "Big Bob", kills: 0 },
  //   { playerId: "sgreen", name: "Samantha Green", nickname: "Green Machine", kills: 1 },
  //   { playerId: "mjones", name: "Mike Jones", nickname: "The Tank", kills: 3 },
  //   { playerId: "tlee", name: "Tom Lee", nickname: "The Ninja", kills: 2 },
  //   { playerId: "jchan", name: "Jackie Chan", nickname: "The Legend", kills: 5 },
  //   { playerId: "jchan2", name: "Jackie Chan", nickname: "The Master", kills: 3 },
  //   { playerId: "tswift", name: "Taylor Swift", nickname: "The Swiftie", kills: 0 },
  //   { playerId: "jkardashian", name: "Kim Kardashian", nickname: "The Queen", kills: 1 },
  //   { playerId: "hpotter", name: "Harry Potter", nickname: "The Chosen One", kills: 7 },
  //   { playerId: "rweasley", name: "Ron Weasley", nickname: "The Sidekick", kills: 2 },
  //   { playerId: "hgryffindor", name: "Hermione Granger", nickname: "The Brain", kills: 4 },
  //   { playerId: "dmalfoy", name: "Draco Malfoy", nickname: "The Slytherin Prince", kills: 3 },
  //   { playerId: "voldemort", name: "Tom Riddle", nickname: "He Who Must Not Be Named", kills: 10 },
  //   { playerId: "dharris", name: "Dumbledore", nickname: "The Wise", kills: 5 },
  //   { playerId: "sblack", name: "Sirius Black", nickname: "The Escape Artist", kills: 1 },
  //   { playerId: "rmcgonagall", name: "Minerva McGonagall", nickname: "The Teacher", kills: 2 },
  //   { playerId: "nhoney", name: "Neville Longbottom", nickname: "The Brave", kills: 1 },
  //   { playerId: "lgryffindor", name: "Luna Lovegood", nickname: "The Dreamer", kills: 0 },
  //   { playerId: "fweasley", name: "Fred Weasley", nickname: "The Prankster", kills: 2 },
  //   { playerId: "gweasley", name: "George Weasley", nickname: "The Jokester", kills: 2 },
  //   { playerId: "pweasley", name: "Percy Weasley", nickname: "The Stickler", kills: 0 },
  //   { playerId: "mmcgonagall", name: "Morris McGonagall", nickname: "The Wizard", kills: 3 },
  //   { playerId: "dmoriarty", name: "James Moriarty", nickname: "The Mastermind", kills: 6 },
  //   { playerId: "ssherlock", name: "Sherlock Holmes", nickname: "The Detective", kills: 4 },
  // ];

  // sort by most kills
  playerInfo.sort((a, b) => b.kills - a.kills);


  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <div className="App">
        <div>
          <h1>Assassin Leaderboard</h1>
          <img src={ivyLogoAssassin} alt="Ivy Assassin" />
          <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            minHeight="50vh"
          >
            <List>
              {playerInfo.map(player => (
                <ListItem key={player.playerId}>
                  <ListItemText primary={`${player.name} (${player.nickname})`} secondary={`Kills: ${player.kills}`} />
                </ListItem>
              ))}
            </List>
          </Box>

        </div>
        <h3> {message} </h3>
      </div>
    </ThemeProvider>
  );
}

export default App;