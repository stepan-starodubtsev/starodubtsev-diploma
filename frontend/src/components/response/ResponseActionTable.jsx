// src/components/response/ResponseActionTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Tooltip, Box, Chip, Switch, TablePagination, Typography
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { format } from 'date-fns'; // Для форматування дати

// Припускаємо, що ResponseActionTypeLabels є в constants.js
// import { ResponseActionTypeLabels } from '../../constants';

const ResponseActionTable = ({
                                 actions,
                                 onEdit,
                                 onDelete,
                                 onToggleEnable, // Функція для зміни статусу is_enabled
                                 // Пагінація (якщо керується ззовні)
                                 page,
                                 rowsPerPage,
                                 count,
                                 onPageChange,
                                 onRowsPerPageChange
                             }) => {

    // Якщо ResponseActionTypeLabels немає, створимо простий мапінг або використовуємо значення напряму
    const getActionTypeLabel = (value) => {
        // Приклад, заміни на імпорт з constants.js, якщо є
        const labels = { "block_ip": "Block IP", "send_email": "Send Email", "create_ticket": "Create Ticket", "isolate_host": "Isolate Host" };
        return labels[value] || value;
    };

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="response actions table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell sx={{ minWidth: 200 }}>Назва Дії</TableCell>
                            <TableCell>Тип Дії</TableCell>
                            <TableCell sx={{ minWidth: 250 }}>Опис</TableCell>
                            <TableCell>Активна</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {actions.length > 0 ? actions.map((action) => (
                            <TableRow key={action.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell>{action.id}</TableCell>
                                <TableCell component="th" scope="row">{action.name}</TableCell>
                                <TableCell>
                                    <Chip label={getActionTypeLabel(action.type?.value || action.type)} size="small" />
                                </TableCell>
                                <TableCell>
                                    <Typography variant="body2" sx={{
                                        whiteSpace: 'nowrap',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        maxWidth: '300px' // Обмеження ширини для довгого опису
                                    }}
                                                title={action.description || ''} // Повний текст при наведенні
                                    >
                                        {action.description || 'N/A'}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Switch
                                        checked={action.is_enabled}
                                        onChange={(e) => onToggleEnable(action.id, e.target.checked)}
                                        size="small"
                                        color="success"
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Редагувати Дію">
                                        <IconButton size="small" onClick={() => onEdit(action)} color="primary">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Видалити Дію">
                                        <IconButton size="small" onClick={() => onDelete(action.id)} color="error">
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={6} align="center">Немає визначених дій реагування</TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={count} // Має бути загальна кількість з сервера (responseStore.totalActions)
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={onPageChange}
                onRowsPerPageChange={onRowsPerPageChange}
                labelRowsPerPage="Рядків на сторінці:"
            />
        </Box>
    );
};

export default ResponseActionTable;