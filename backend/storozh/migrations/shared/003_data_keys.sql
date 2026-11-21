-- Ключи данных граждан (DEK) для конвертного шифрования shared.crypto (Разработчик 2).
-- DEK зашифрован мастер-ключом из окружения. Удалили строку — все данные гражданина нечитаемы (crypto-shredding).
-- Доступ только у роли storozh_shared: контексты шифруют через shared.crypto, сами ключи не читают.
CREATE TABLE shared.data_keys (
    citizen_id  uuid        PRIMARY KEY,
    dek_enc     bytea       NOT NULL,            -- nonce(12) || AES-256-GCM(master_key, dek)
    created_at  timestamptz NOT NULL DEFAULT now()
);

DO $$
DECLARE ctx text;
BEGIN
    FOREACH ctx IN ARRAY ARRAY['platform', 'documents', 'guard', 'assistant'] LOOP
        EXECUTE format('REVOKE ALL ON shared.data_keys FROM %I', 'storozh_' || ctx);
    END LOOP;
END $$;
