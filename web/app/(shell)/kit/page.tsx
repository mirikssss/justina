import { Badge, Button, Card, EmptyState, Icon, PageHeader } from "@/components/mygov";

// Витрина кита (Разработчик 3): всё, из чего собираются страницы. Стиль — как у живого my.gov.uz.
export default function KitPage() {
  return (
    <div className="dcol">
      <div className="hero">
        <h1>Xush kelibsiz!</h1>
        <p>Баннер с градиентом портала: #0068e0 → #00dc82.</p>
        <label className="search"><Icon name="search" /><input placeholder="Qidiruv uchun matn kiriting" /></label>
      </div>
      <PageHeader title="Kit" subtitle="Компоненты MyGov" />
      <Card title="Tugmalar" icon="grid">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Button>Asosiy</Button>
          <Button variant="ghost">Ikkinchi darajali</Button>
          <Button small>Kichik</Button>
          <button className="btn-login" type="button"><span className="bi"><Icon name="user" size={16} /></span>Kirish</button>
        </div>
      </Card>
      <Card title="Holatlar" icon="check2">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Badge tone="good">Amalda</Badge>
          <Badge tone="warn">Muddati tugayapti</Badge>
          <Badge tone="crit">Bekor qilingan</Badge>
          <Badge tone="info">Bajarilgan</Badge>
          <Badge tone="new">YANGI</Badge>
        </div>
      </Card>
      <EmptyState title="Bo'sh" hint="Keyin nima qilish kerakligi haqida maslahat" />
    </div>
  );
}
