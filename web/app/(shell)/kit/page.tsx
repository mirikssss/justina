import { Badge, Button, Card, EmptyState, PageHeader } from "@/components/mygov";

// Витрина кита (Разработчик 3): всё, из чего собираются страницы, на одной странице.
export default function KitPage() {
  return (
    <div className="space-y-5">
      <PageHeader title="Kit" subtitle="Компоненты MyGov" />
      <Card title="Кнопки">
        <div className="flex gap-3">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="danger">Danger</Button>
        </div>
      </Card>
      <Card title="Статусы">
        <div className="flex gap-2">
          <Badge tone="good">active</Badge>
          <Badge tone="warn">expires</Badge>
          <Badge tone="crit">critical</Badge>
          <Badge tone="info">new</Badge>
          <Badge>revoked</Badge>
        </div>
      </Card>
      <EmptyState title="Пусто" hint="Подсказка, что сделать дальше" />
    </div>
  );
}
