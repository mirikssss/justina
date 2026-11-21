-- Резюме принадлежит гражданину: GET /assist/documents/{id}/summary отдаёт только свои.
ALTER TABLE summaries ADD COLUMN citizen_id uuid;
CREATE INDEX summaries_lookup ON summaries (document_id, lang, version_no DESC);
