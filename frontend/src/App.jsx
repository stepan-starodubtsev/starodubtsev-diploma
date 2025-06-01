// src/App.js
import React, { useState, useMemo, createContext } from 'react';
import {Box, CssBaseline, ThemeProvider} from '@mui/material';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'; // Додано Navigate

import { getAppTheme } from './theme'; // Наш файл з темою

// Компоненти макету
import Header from './components/layout/Header';
import DevicesPage from "./pages/DevicesPage.jsx";
import IoCSourcesPage from "./pages/IoCSourcesPage.jsx";
import APTGroupsPage from "./pages/APTGroupsPage.jsx";
import IndicatorsPage from "./pages/IndicatorsPage.jsx";
import CorrelationRulesPage from "./pages/CorrelationRulesPage.jsx";
import OffencesPage from "./pages/OffencesPage.jsx";
import ResponsePage from "./pages/ResponsePage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx"; // <--- НОВИЙ ХЕДЕР

// Приклади сторінок (створи їх у src/pages/)
// const ProfilePage = () => <div>Профіль Користувача</div>; // Заглушка


export const ColorModeContext = createContext({ toggleColorMode: () => {} });

function App() {
    const [mode, setMode] = useState('dark'); // <--- Змінено на 'light' за замовчуванням

    const colorMode = useMemo(
        () => ({
            toggleColorMode: () => {
                setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
            },
        }),
        [],
    );

    const theme = useMemo(() => getAppTheme(mode), [mode]);

    return (
        <ColorModeContext.Provider value={colorMode}>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <BrowserRouter>
                    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}> {/* Змінено на column */}
                        <Header /> {/* <--- Додано Хедер */}

                        <Box
                            component="main"
                            sx={{
                                flexGrow: 1,
                                p: 3, // Використовуємо p для padding з теми
                                overflowY: 'auto',
                                backgroundColor: theme.palette.background.default
                            }}
                        >
                            <Routes>
                                <Route path="/" element={<DashboardPage />} />
                                <Route path="/devices" element={<DevicesPage />} />
                                <Route path="/ioc-sources" element={<IoCSourcesPage />} />
                                <Route path="/apt-groups" element={<APTGroupsPage />} />
                                <Route path="/iocs" element={<IndicatorsPage />} />
                                <Route path="/correlation-rules" element={<CorrelationRulesPage />} />
                                <Route path="/offences" element={<OffencesPage />} />
                                <Route path="/responses" element={<ResponsePage />} />
                                {/* <Route path="/profile" element={<ProfilePage />} /> */}

                                {/* Приклад редиректу, якщо шлях не знайдено */}
                                <Route path="*" element={<Navigate to="/" replace />} />
                            </Routes>
                        </Box>
                    </Box>
                </BrowserRouter>
            </ThemeProvider>
        </ColorModeContext.Provider>
    );
}

export default App;

// Не забудь імпортувати Box з @mui/material, якщо ще не зроблено
// import { Box } from '@mui/material'; (має бути вже через ThemeProvider/CssBaseline)