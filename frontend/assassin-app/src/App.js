
import './App.css';
// MUI imports
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import BlockIcon from '@mui/icons-material/Block';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
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
  const gameName = 'ivy';

  const [isLoading, setIsLoading] = React.useState(true);
  const [playerInfo, setPlayerInfo] = React.useState([]);

  React.useEffect(() => {
    fetch(`${API_URL}/api/game-stats/${gameName}`)
      .then(response => response.json())
      .then(game_stats => {
        const playerIds = Object.keys(game_stats);
        Promise.all(playerIds.map(netid => fetch(`${API_URL}/api/players/${netid}`)))
          .then(responses => Promise.all(responses.map(response => response.json())))
          .then(players => {
            const updatedPlayerInfo = playerIds.map(netid => {
              const playerKills = game_stats[netid]["kills"];
              const playerIsAlive = game_stats[netid]["isAlive"];
              const playerInfo = players.find(player => player.netid === netid);
              console.log(playerInfo.name, playerInfo.nickname, playerKills, playerIsAlive)
              return {
                netid,
                name: playerInfo.name,
                nickname: playerInfo.nickname,
                fullAssassinName: playerInfo.fullAssassinName,
                kills: playerKills,
                isAlive: playerIsAlive
              };
            });
            setPlayerInfo(updatedPlayerInfo);
            setIsLoading(false);
          });
      });
  }, []);


  const [message, setMessage] = useState('');
  useEffect(() => {
    fetch(`${API_URL}/hello_world`)
      .then(response => response.text())
      .then(data => setMessage(data));
  }, []);

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
              {isLoading && (<CircularProgress />)}
              {!isLoading && 
              (<List>
                {playerInfo.map(player => (
                  <ListItem key={player.playerId}>
                    <ListItemText primary={`${player.fullAssassinName}`} secondary={`Kills: ${player.kills}`} />
                    {!player.isAlive && <BlockIcon />}
                  </ListItem>
                ))}
              </List>)}
            </Box>
        </div>
        <h3> {message} </h3>
      </div>
    </ThemeProvider>
  );
}

export default App;