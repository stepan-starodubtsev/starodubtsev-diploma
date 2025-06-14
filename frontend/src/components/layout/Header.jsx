// src/components/layout/Header.jsx
import React from 'react';
import { AppBar, Toolbar, Typography, Button, IconButton, Box, useTheme } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom'; // Для навігації
import Brightness4Icon from '@mui/icons-material/Brightness4'; // Іконка для темної теми
import Brightness7Icon from '@mui/icons-material/Brightness7'; // Іконка для світлої теми
import SecurityIcon from '@mui/icons-material/Security'; // Іконка для логотипу

// Імпортуємо ColorModeContext для перемикання теми
import { ColorModeContext } from '../../App'; // Припускаємо, що App.js знаходиться на два рівні вище

const NavItem = ({ to, children }) => {
    const location = useLocation();
    const isActive = location.pathname === to;

    return (
        <Button
            component={RouterLink}
            to={to}
            sx={{
                color: 'inherit',
                textTransform: 'none',
                fontWeight: isActive ? 'bold' : 'normal',
                '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.08)' // Легкий ефект при наведенні
                },
                margin: theme => theme.spacing(0, 1) // Відступи між кнопками
            }}
        >
            {children}
        </Button>
    );
};


const Header = () => {
    const theme = useTheme();
    const colorMode = React.useContext(ColorModeContext); // Отримуємо контекст для перемикання

    // Пункти меню (адаптуй під свої потреби та ролі користувачів)
    // Тут можна додати логіку умовного рендерингу на основі authStore, як у тебе було в Sidebar
    const menuItems = [
        { label: 'Дашборд', path: '/' },
        { label: 'Пристрої', path: '/devices' },
        { label: 'Джерела IoC', path: '/ioc-sources' },
        { label: 'APT Угруповання', path: '/apt-groups' },
        { label: 'Індикатори (IoC)', path: '/iocs' },
        { label: 'Правила Кореляції', path: '/correlation-rules' },
        { label: 'Офенси', path: '/offences' },
        { label: 'Правила реагування', path: '/responses' },
        { label: 'Профіль', path: '/profile' }, // Якщо є автентифікація
    ];


    return (
        <AppBar position="static" elevation={1} sx={{ marginBottom: theme.spacing(2) }}>
            <Toolbar>
                <SecurityIcon sx={{ mr: 2 }} /> {/* Іконка логотипу */}
                <Typography variant="h6" component="div" sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit' }} component={RouterLink} to="/">
                    SIEM ЗСУ
                </Typography>

                <Box>
                    {menuItems.map((item) => (
                        <NavItem key={item.path} to={item.path}>
                            {item.label}
                        </NavItem>
                    ))}
                </Box>

                <IconButton sx={{ ml: 1 }} onClick={colorMode.toggleColorMode} color="inherit">
                    {theme.palette.mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
                </IconButton>
            </Toolbar>
        </AppBar>
    );
};

export default Header;