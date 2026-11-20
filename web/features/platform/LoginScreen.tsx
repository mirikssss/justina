import { Button, Card } from "@/components/mygov";

// TODO(Разработчик 2): POST /auth/telegram/start -> ссылка на бота -> /auth/callback
export function LoginScreen() {
  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card title="Вход в «Мои документы»">
        <p className="mb-4 text-sm text-muted">Вход через Telegram-бота: ссылка одноразовая и действует 5 минут.</p>
        <Button disabled>Войти через Telegram</Button>
      </Card>
    </div>
  );
}
