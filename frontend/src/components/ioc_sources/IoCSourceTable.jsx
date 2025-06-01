// src/components/ioc_sources/IoCSourceTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Tooltip, Box, Chip, Link as MuiLink, TablePagination
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'; // Для "Fetch IoCs"
import { format } from 'date-fns'; // Для форматування дати

const IoCSourceTable = ({
                            sources,
                            onEdit,
                            onDelete,
                            onFetchIoCs,
                            // Для серверної пагінації (поки не використовуємо, але можна додати)
                            // page,
                            // rowsPerPage,
                            // count,
                            // onPageChange,
                            // onRowsPerPageChange
                        }) => {

    // Клієнтська пагінація для прикладу
    const [page, setPage] = React.useState(0);
    const [rowsPerPage, setRowsPerPage] = React.useState(10);

    const handleChangePage = (event, newPage) => {
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    const displayedSources = sources.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

    return (
        <Box>
            <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="ioc sources table">
                    <TableHead sx={{ backgroundColor: (theme) => theme.palette.action.hover }}>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell>Назва</TableCell>
                            <TableCell>Тип</TableCell>
                            <TableCell>URL</TableCell>
                            <TableCell>Активне</TableCell>
                            <TableCell>Останнє Завантаження</TableCell>
                            <TableCell align="center">Дії</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {displayedSources.length > 0 ? displayedSources.map((source) => (
                            <TableRow key={source.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell>{source.id}</TableCell>
                                <TableCell component="th" scope="row">{source.name}</TableCell>
                                <TableCell>
                                    <Chip label={source.type?.value || source.type} size="small" />
                                </TableCell>
                                <TableCell>
                                    {source.url ? (
                                        <MuiLink href={source.url} target="_blank" rel="noopener noreferrer">
                                            {source.url.length > 50 ? `${source.url.substring(0, 47)}...` : source.url}
                                        </MuiLink>
                                    ) : 'N/A'}
                                </TableCell>
                                <TableCell>
                                    <Chip label={source.is_enabled ? 'Так' : 'Ні'} color={source.is_enabled ? 'success' : 'default'} size="small" />
                                </TableCell>
                                <TableCell>
                                    {source.last_fetched
                                        ? format(new Date(source.last_fetched), 'yyyy-MM-dd HH:mm:ss')
                                        : 'Ніколи'}
                                </TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Завантажити IoC">
                                        <IconButton size="small" onClick={() => onFetchIoCs(source.id)} color="secondary">
                                            <PlayCircleOutlineIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Редагувати">
                                        <IconButton size="small" onClick={() => onEdit(source)} color="primary">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Видалити">
                                        <IconButton size="small" onClick={() => onDelete(source.id)} color="error">
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        )) : (
                            <TableRow>
                                <TableCell colSpan={7} align="center">
                                    Немає даних про джерела IoC
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50]}
                component="div"
                count={sources.length} // Для клієнтської пагінації
                // count={count} // Для серверної пагінації
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                labelRowsPerPage="Рядків на сторінці:"
            />
        </Box>
    );
};

export default IoCSourceTable;