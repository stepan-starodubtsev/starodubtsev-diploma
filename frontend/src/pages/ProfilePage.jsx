// src/pages/ProfilePage.jsx
import React from 'react';
import {Box, Typography, Paper, Avatar, Grid, Divider, Button} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
// import { observer } from 'mobx-react-lite'; // Якщо будеш використовувати authStore
// import { authStore } from '../stores/authStore'; // Приклад, якщо authStore буде

// Заглушка даних користувача, поки немає authStore
const MOCKED_USER_DATA = {
    name: "Іван Іваненко",
    username: "user_zsu",
    role: "Аналітик Безпеки", // Або "Адміністратор"
    email: "ivan.ivanenko@example.mil.gov.ua",
    department: "Кібернетичний Центр",
    lastLogin: new Date().toLocaleString('uk-UA'),
};

const ProfilePage = () => {
    // Коли буде authStore:
    // const user = authStore.user;
    // if (!authStore.isAuthenticated || !user) {
    //   return <Typography>Будь ласка, увійдіть для перегляду профілю.</Typography>;
    // }
    const user = MOCKED_USER_DATA; // Використовуємо заглушку

    return (
        <Paper elevation={3} sx={{ p: { xs: 2, sm: 3 }, maxWidth: 700, margin: 'auto' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Avatar sx={{ width: 64, height: 64, mr: 2, bgcolor: 'primary.main' }}>
                    <PersonIcon sx={{ fontSize: 40 }} />
                </Avatar>
                <Typography variant="h4" component="h1">
                    Профіль Користувача
                </Typography>
            </Box>

            <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" color="text.secondary">Повне ім'я:</Typography>
                    <Typography variant="h6">{user.name}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" color="text.secondary">Логін:</Typography>
                    <Typography variant="h6">{user.username}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" color="text.secondary">Роль:</Typography>
                    <Typography variant="body1">{user.role}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" color="text.secondary">Email:</Typography>
                    <Typography variant="body1">{user.email}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" color="text.secondary">Підрозділ/Департамент:</Typography>
                    <Typography variant="body1">{user.department}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" color="text.secondary">Останній вхід:</Typography>
                    <Typography variant="body1">{user.lastLogin}</Typography>
                </Grid>
            </Grid>

            {/* Тут можна додати кнопки для зміни пароля, налаштувань тощо, коли буде відповідний функціонал */}
            <Divider sx={{my:3}}/>
            <Button variant='outlined'>Змінити пароль</Button>
        </Paper>
    );
};

export default ProfilePage;