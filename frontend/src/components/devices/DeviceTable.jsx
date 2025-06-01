// src/components/devices/DeviceTable.jsx
import React from 'react';
import {
    Box,
    Chip,
    IconButton,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TablePagination,
    TableRow,
    Tooltip
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import InfoIcon from '@mui/icons-material/Info'; // Для кнопки "Статус"
// import deviceStore from '../../stores/deviceStore'; // Пагінація буде керуватися зі сторінки

const DeviceTable = ({ devices, onEdit, onDelete, onGetStatus /*, інші обробники */ }) => {
    // Пагінація (якщо керується локально в компоненті, або краще з MobX стору)
    const [page, setPage] = React.useState(0);
    const [rowsPerPage, setRowsPerPage] = React.useState(10);

    const handleChangePage = (event, newPage) => {
        setPage(newPage);
        // Якщо пагінація на сервері, викликати:
        // deviceStore.setPagination(newPage, rowsPerPage);
    };

    const handleChangeRowsPerPage = (event) => {
        const newRowsPerPage = parseInt(event.target.value, 10);
        setRowsPerPage(newRowsPerPage);
        setPage(0);
        // Якщо пагінація на сервері, викликати:
        // deviceStore.setPagination(0, newRowsPerPage);
    };

    const getStatusChipColor = (status) => {
        switch (status) {
            case 'reachable': return 'success';
            case 'unreachable': return 'error';
            case 'configuring': return 'info';
            case 'error': return 'error';
            default: return 'default';
        }
    };


    // Логіка для відображення поточного зрізу даних з пагінацією
    const displayedDevices = devices.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="simple table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell>Назва</TableCell>
                            <TableCell>Хост</TableCell>
                            <TableCell>Порт</TableCell>
                            <TableCell>Тип</TableCell>
                            <TableCell>Статус</TableCell>
                            <TableCell>Версія ОС</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {displayedDevices.length > 0 ? displayedDevices.map((device) => (
                            <TableRow
                                key={device.id}
                                sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                            >
                                <TableCell component="th" scope="row">{device.id}</TableCell>
                                <TableCell>{device.name}</TableCell>
                                <TableCell>{device.host}</TableCell>
                                <TableCell>{device.port}</TableCell>
                                <TableCell>{device.device_type?.value || device.device_type}</TableCell> {/* Обробка Enum */}
                                <TableCell>
                                    <Chip
                                        label={device.status?.value || device.status || 'N/A'}
                                        color={getStatusChipColor(device.status?.value || device.status)}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>{device.os_version || 'N/A'}</TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Оновити Статус">
                                        <IconButton size="small" onClick={() => onGetStatus(device.id)} color="info">
                                            <InfoIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Редагувати">
                                        <IconButton size="small" onClick={() => onEdit(device)} color="primary">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Видалити">
                                        <IconButton size="small" onClick={() => onDelete(device.id)} color="error">
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                    {/* Додай кнопки для інших дій тут, наприклад: */}
                                    {/* <Tooltip title="Налаштувати Syslog">
                    <IconButton size="small" onClick={() => onConfigureSyslog(device.id)} color="secondary">
                      <SettingsEthernetIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Заблокувати IP (приклад)">
                     <IconButton size="small" onClick={() => onBlockIp(device.id)} sx={{color: 'orange'}}>
                        <BlockIcon />
                    </IconButton>
                  </Tooltip>
                   */}
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={8} align="center">
                                    Немає даних про пристрої
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                // count={deviceStore.totalDevices} // Якщо пагінація на сервері
                count={devices.length} // Для пагінації на клієнті
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
            />
        </Box>
    );
};

export default DeviceTable;