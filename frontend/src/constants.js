// src/utils/constants.js (або де ти його розмістив)

// --- Для Джерел IoC (ioc_sources) ---
export const IoCSourceTypeEnum = {
    MISP: "misp",
    OPENCTI: "opencti",
    STIX_FEED: "stix_feed",
    CSV_URL: "csv_url",
    INTERNAL: "internal",
    MOCK_APT_REPORT: "mock_apt_report" // Використовується в seed_data.py
};

// Масив для використання в Select компонентах MUI (приклад для Джерел IoC)
export const IoCSourceTypeLabels = [
    {value: IoCSourceTypeEnum.MISP, label: "MISP"},
    {value: IoCSourceTypeEnum.OPENCTI, label: "OpenCTI"},
    {value: IoCSourceTypeEnum.STIX_FEED, label: "STIX Feed"},
    {value: IoCSourceTypeEnum.CSV_URL, label: "CSV via URL"},
    {value: IoCSourceTypeEnum.INTERNAL, label: "Внутрішнє джерело"},
    {value: IoCSourceTypeEnum.MOCK_APT_REPORT, label: "Імітація (Звіт APT)"}
];


// --- Для Індикаторів Компрометації (indicators) ---
export const IoCTypeEnum = {
    IPV4_ADDR: "ipv4-addr",
    IPV6_ADDR: "ipv6-addr",
    DOMAIN_NAME: "domain-name",
    URL: "url",
    MD5_HASH: "file-hash-md5",
    SHA1_HASH: "file-hash-sha1",
    SHA256_HASH: "file-hash-sha256",
    EMAIL_ADDR: "email-addr"
    // Додай інші типи, якщо вони є в IoCTypeEnum на бекенді
};

export const IoCTypeLabels = [
    {value: IoCTypeEnum.IPV4_ADDR, label: "IPv4 Адреса"},
    {value: IoCTypeEnum.IPV6_ADDR, label: "IPv6 Адреса"},
    {value: IoCTypeEnum.DOMAIN_NAME, label: "Доменне Ім'я"},
    {value: IoCTypeEnum.URL, label: "URL"},
    {value: IoCTypeEnum.MD5_HASH, label: "MD5 Хеш"},
    {value: IoCTypeEnum.SHA1_HASH, label: "SHA1 Хеш"},
    {value: IoCTypeEnum.SHA256_HASH, label: "SHA256 Хеш"},
    {value: IoCTypeEnum.EMAIL_ADDR, label: "Email Адреса"}
];


// --- Для APT Угруповань (apt_groups) ---
export const APTGroupMotivationsEnum = {
    ESPIONAGE: "espionage",
    FINANCIAL_GAIN: "financial_gain",
    SABOTAGE: "sabotage",
    HACKTIVISM: "hacktivism",
    UNKNOWN: "unknown"
};

export const APTGroupMotivationLabels = [
    {value: APTGroupMotivationsEnum.ESPIONAGE, label: "Шпигунство"},
    {value: APTGroupMotivationsEnum.FINANCIAL_GAIN, label: "Фінансова вигода"},
    {value: APTGroupMotivationsEnum.SABOTAGE, label: "Саботаж/Руйнування"},
    {value: APTGroupMotivationsEnum.HACKTIVISM, label: "Активізм"},
    {value: APTGroupMotivationsEnum.UNKNOWN, label: "Невідома"}
];

export const APTGroupSophisticationEnum = {
    HIGH: "high",
    MEDIUM: "medium",
    LOW: "low",
    UNKNOWN: "unknown"
};

export const APTGroupSophisticationLabels = [
    {value: APTGroupSophisticationEnum.HIGH, label: "Високий"},
    {value: APTGroupSophisticationEnum.MEDIUM, label: "Середній"},
    {value: APTGroupSophisticationEnum.LOW, label: "Низький"},
    {value: APTGroupSophisticationEnum.UNKNOWN, label: "Невідомий"}
];


// --- Для Правил Кореляції (correlation_rules) ---
export const CorrelationRuleTypeEnum = {
    IOC_MATCH_IP: "ioc_match_ip",
    // Додай інші типи правил, які ми визначили (IOC_MATCH_DOMAIN, IOC_MATCH_URL, IOC_MATCH_HASH - якщо вони є)
    THRESHOLD_LOGIN_FAILURES: "threshold_login_failures",
    THRESHOLD_DATA_EXFILTRATION: "threshold_data_exfiltration"
};

export const CorrelationRuleTypeLabels = [
    {value: CorrelationRuleTypeEnum.IOC_MATCH_IP, label: "Зіставлення IP з IoC"},
    {value: CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES, label: "Поріг: Невдалі спроби входу"},
    {value: CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION, label: "Поріг: Ексфільтрація даних"}
];

export const EventFieldToMatchTypeEnum = { // Використовується в правилах кореляції
    SOURCE_IP: "source_ip",
    DESTINATION_IP: "destination_ip",
    USERNAME: "username",
    HOSTNAME: "hostname",
    EVENT_MESSAGE: "message",
    NETWORK_BYTES_TOTAL: "network_bytes_total"
    // Додай інші поля з CommonEventSchema, за якими можна фільтрувати/агрегувати
};

export const EventFieldToMatchLabels = [
    {value: EventFieldToMatchTypeEnum.SOURCE_IP, label: "IP Джерела (події)"},
    {value: EventFieldToMatchTypeEnum.DESTINATION_IP, label: "IP Призначення (події)"},
    {value: EventFieldToMatchTypeEnum.USERNAME, label: "Ім'я користувача (події)"},
    {value: EventFieldToMatchTypeEnum.HOSTNAME, label: "Ім'я хоста (події)"},
    {value: EventFieldToMatchTypeEnum.EVENT_MESSAGE, label: "Повідомлення (події)"},
    {value: EventFieldToMatchTypeEnum.NETWORK_BYTES_TOTAL, label: "Загальна к-ть байт (події)"}
];

// IoCTypeToMatchEnum в правилах кореляції - це той самий, що й IoCTypeEnum для індикаторів.


// --- Для Офенсів (offences) ---
export const OffenceSeverityEnum = {
    LOW: "low",
    MEDIUM: "medium",
    HIGH: "high",
    CRITICAL: "critical"
};

export const OffenceSeverityLabels = [
    {value: OffenceSeverityEnum.LOW, label: "Низька"},
    {value: OffenceSeverityEnum.MEDIUM, label: "Середня"},
    {value: OffenceSeverityEnum.HIGH, label: "Висока"},
    {value: OffenceSeverityEnum.CRITICAL, label: "Критична"}
];

export const OffenceStatusEnum = {
    NEW: "new",
    IN_PROGRESS: "in_progress",
    CLOSED_FALSE_POSITIVE: "closed_false_positive",
    CLOSED_TRUE_POSITIVE: "closed_true_positive",
    CLOSED_OTHER: "closed_other"
};

export const OffenceStatusLabels = [
    {value: OffenceStatusEnum.NEW, label: "Новий"},
    {value: OffenceStatusEnum.IN_PROGRESS, label: "В обробці"},
    {value: OffenceStatusEnum.CLOSED_FALSE_POSITIVE, label: "Закритий (Хибне спрац.)"},
    {value: OffenceStatusEnum.CLOSED_TRUE_POSITIVE, label: "Закритий (Підтверджено)"},
    {value: OffenceStatusEnum.CLOSED_OTHER, label: "Закритий (Інше)"}
];


// --- Для Дій та Пайплайнів Реагування (response) ---
export const ResponseActionTypeEnum = {
    BLOCK_IP: "block_ip",
    UNBLOCK_IP: "unblock_ip",
    SEND_EMAIL: "send_email",
    CREATE_TICKET: "create_ticket",
    ISOLATE_HOST: "isolate_host"
};

export const ResponseActionTypeLabels = [
    {value: ResponseActionTypeEnum.BLOCK_IP, label: "Блокувати IP"},
    {value: ResponseActionTypeEnum.UNBLOCK_IP, label: "Розблокувати IP"},
    {value: ResponseActionTypeEnum.SEND_EMAIL, label: "Надіслати Email"},
    {value: ResponseActionTypeEnum.CREATE_TICKET, label: "Створити Тікет"},
    {value: ResponseActionTypeEnum.ISOLATE_HOST, label: "Ізолювати Хост"}
];

export const IoCTypeToMatchEnum = {
    IPV4_ADDR: "ipv4-addr",
    IPV6_ADDR: "ipv6-addr"
}
// --- Інші константи ---
// Наприклад, для пагінації, якщо ти хочеш мати їх централізовано
export const DEFAULT_ROWS_PER_PAGE_OPTIONS = [5, 10, 25, 50, 100];