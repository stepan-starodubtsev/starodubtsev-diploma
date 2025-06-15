// src/components/layout/Header.jsx
import React from 'react';
import { AppBar, Toolbar, Typography, Button, IconButton, Box, useTheme } from '@mui/material';
import {Link as RouterLink, NavLink, useLocation, useNavigate} from 'react-router-dom'; // Для навігації
import Brightness4Icon from '@mui/icons-material/Brightness4'; // Іконка для темної теми
import Brightness7Icon from '@mui/icons-material/Brightness7'; // Іконка для світлої теми
import SecurityIcon from '@mui/icons-material/Security'; // Іконка для логотипу

// Імпортуємо ColorModeContext для перемикання теми
import { ColorModeContext } from '../../App';
import {observer} from "mobx-react-lite";
import authStore from "../../stores/authStore.js";
import {DarkModeOutlined, LightModeOutlined} from "@mui/icons-material"; // Припускаємо, що App.js знаходиться на два рівні вище

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


const Header = observer(() => {
    const theme = useTheme();
    const colorMode = React.useContext(ColorModeContext);
    const navigate = useNavigate();

    const handleLogout = () => {
        authStore.logout();
        navigate('/login');
    };

    const menuItems = [
        { path: '/', label: 'Дашборд' },
        { path: '/devices', label: 'Пристрої' },
        { path: '/apt-groups', label: 'APT угруповування' },
        { path: '/ioc-sources', label: 'Джерела IoC' },
        { path: '/indicators', label: 'Індикатори компрометації' },
        { path: '/correlation', label: 'Правила кореляції' },
        { path: '/offences', label: 'Інциденти' },
        { path: '/response', label: 'Реагування' },
    ];

    return (
        <AppBar position="static" color="default" elevation={1}>
            <Toolbar>
                <Typography variant="h6" component={NavLink} to="/" sx={{ textDecoration: 'none', color: 'inherit' }}>
                    SIEM ЗСУ
                </Typography>
                <Box sx={{ flexGrow: 1, ml: 3, display: 'flex' }}>
                    {menuItems.map((item) => (
                        <NavItem key={item.path} to={item.path}>
                            {item.label}
                        </NavItem>
                    ))}
                    {/* Посилання тільки для адміна */}
                    {authStore.isAdmin && (
                        <NavItem to="/users">Користувачі</NavItem>
                    )}
                </Box>

                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography sx={{ mr: 2 }}>
                        {authStore.user?.username}
                    </Typography>
                    <IconButton onClick={colorMode.toggleColorMode} color="inherit">
                        {theme.palette.mode === 'dark' ? <LightModeOutlined /> : <DarkModeOutlined />}
                    </IconButton>
                    <Button color="inherit" onClick={handleLogout}>
                        Вийти
                    </Button>
                </Box>
            </Toolbar>
        </AppBar>
    );
});

export default Header;