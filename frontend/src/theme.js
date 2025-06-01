// src/theme.js
import { createTheme } from '@mui/material/styles';
import { grey, blue, green, pink } from '@mui/material/colors'; // Додав pink для акценту

// Функція для генерації токенів кольорів (можеш її залишити або спростити)
export const tokens = (mode) => ({
    grey: { // Змінимо відтінки для кращого вигляду на світлій темі
        100: mode === 'light' ? grey[100] : '#1F2A40', // Темний для тексту на світлому фоні
        200: mode === 'light' ? grey[200] : grey[700],
        300: mode === 'light' ? grey[300] : grey[600],
        400: mode === 'light' ? grey[400] : grey[500],
        500: mode === 'light' ? grey[500] : grey[400],
        600: mode === 'light' ? grey[600] : grey[300], // Світлий для тексту на темному фоні
        700: mode === 'light' ? grey[700] : grey[200],
        800: mode === 'light' ? grey[800] : grey[100],
        900: mode === 'light' ? grey[900] : '#e0e0e0',
    },
    primary: { // Головний колір (наприклад, синій)
        100: mode === 'light' ? blue[50] : blue[900],
        200: mode === 'light' ? blue[100] : blue[800],
        300: mode === 'light' ? blue[200] : blue[700],
        400: mode === 'light' ? blue[300] : blue[600],
        main: mode === 'light' ? blue[500] : blue[400], // Основний відтінок
        600: mode === 'light' ? blue[600] : blue[300],
        700: mode === 'light' ? blue[700] : blue[200],
        800: mode === 'light' ? blue[800] : blue[100],
        900: mode === 'light' ? blue[900] : blue[50],
    },
    secondary: { // Додатковий колір (наприклад, рожевий акцент)
        main: mode === 'light' ? pink.A400 : pink.A200,
    },
    greenAccent: { // Твій зелений акцент
        300: mode === 'light' ? green[100] : green[400], // Адаптуємо для світлої теми
        500: mode === 'light' ? green[400] : green[200],
        700: mode === 'light' ? green[700] : green[100],
    },
    background: {
        default: mode === 'light' ? grey[100] : '#121212', // Світло-сірий для світлої теми
        paper: mode === 'light' ? '#ffffff' : '#1E2D3F', // Білий для "паперу" на світлій
    },
    text: {
        primary: mode === 'light' ? grey[900] : grey[100],
        secondary: mode === 'light' ? grey[700] : grey[400],
    }
});

export const getAppTheme = (mode = 'light') => { // Встановлюємо 'light' за замовчуванням
    const currentTokens = tokens(mode); // Отримуємо токени для поточного режиму

    return createTheme({
        palette: {
            mode: mode,
            primary: {
                main: currentTokens.primary.main,
                // Можеш додати light, dark, contrastText, якщо потрібно
            },
            secondary: {
                main: currentTokens.secondary.main,
            },
            // Можеш залишити neutral, якщо він використовується, або прибрати
            // neutral: {
            //   dark: currentTokens.grey[700],
            //   main: currentTokens.grey[500],
            //   light: currentTokens.grey[100],
            // },
            background: {
                default: currentTokens.background.default,
                paper: currentTokens.background.paper,
            },
            text: {
                primary: currentTokens.text.primary,
                secondary: currentTokens.text.secondary,
            },
            // Додамо кольори з tokens напряму в палітру, якщо зручно
            customGrey: currentTokens.grey,
            customGreenAccent: currentTokens.greenAccent,
        },
        typography: {
            fontFamily: ['"Inter var"', 'Roboto', '"Helvetica"', 'Arial', 'sans-serif'].join(','),
            fontSize: 14, // Трохи збільшимо базовий розмір
            h1: { fontSize: "2.2rem", fontWeight: 700 },
            h2: { fontSize: "2rem", fontWeight: 600 },
            h3: { fontSize: "1.75rem", fontWeight: 600 },
            h4: { fontSize: "1.5rem", fontWeight: 500 },
            h5: { fontSize: "1.25rem", fontWeight: 500 },
            h6: { fontSize: "1.1rem", fontWeight: 500 },
            // ... (інші налаштування типографії)
        },
        components: {
            MuiAppBar: {
                styleOverrides: {
                    root: {
                        // Стилі для AppBar, якщо потрібно
                        // backgroundColor: mode === 'light' ? currentTokens.primary.main : currentTokens.primary[800], // Наприклад
                    }
                }
            },
            MuiButton: {
                styleOverrides: {
                    root: {
                        borderRadius: '8px',
                        textTransform: 'none', // Прибираємо ALL CAPS для кнопок
                    },
                },
            },
            // ... інші компоненти
        },
    });
};