# Sistema de Controle de Estoque com Reservas

## Visão Geral

O sistema implementa um controle inteligente de estoque que reserva temporariamente produtos quando os clientes enviam uma cotação (quote request). Isso evita vendas duplas e garante que o estoque esteja disponível durante a negociação com o cliente.

## Como Funciona

### 1. Quando um Cliente Faz uma Cotação

Ao enviar um pedido de cotação pelo carrinho de compras:

1. **Validação de Disponibilidade**: O sistema verifica se há estoque disponível considerando reservas ativas
2. **Criação de Reservas**: Para cada item no carrinho, cria uma reserva temporária de estoque
3. **Duração da Reserva**: Por padrão, as reservas duram **30 minutos**
4. **Email de Notificação**: O admin recebe um email com os IDs das reservas criadas
5. **Limpeza do Carrinho**: O carrinho é limpo após a reserva bem-sucedida

### 2. Disponibilidade de Produtos

O sistema agora diferencia:

- **`stock_quantity`**: Quantidade física em estoque
- **`available_quantity`**: Quantidade disponível para venda (stock - reservado)
- **`is_available`**: Produto disponível para compra (considera reservas)

**Exemplo**:
- Stock físico: 5 unidades
- Reservas ativas: 2 unidades
- Disponível para venda: 3 unidades
- Status mostrado: "3 available" ou "Reserved" se todas unidades estiverem reservadas

### 3. Gestão de Reservas no Admin

O admin tem um painel dedicado em `/admin/reservations/` com as seguintes funcionalidades:

#### Ações Disponíveis

**✅ Confirmar Venda** (`confirm_reservation`)
- Converte a reserva em venda confirmada
- **Reduz o estoque físico** automaticamente
- Marca o jogo como vendido se o estoque chegar a zero
- Permite adicionar notas administrativas

**❌ Cancelar Reserva** (`cancel_reservation`)
- Libera o estoque reservado
- Torna o produto disponível novamente
- Útil quando cliente desiste ou não responde
- Permite adicionar motivo do cancelamento

**⏰ Estender Tempo** (`extend_reservation`)
- Prolonga a validade da reserva
- Padrão: +30 minutos (configurável)
- Útil durante negociações com o cliente

**🔄 Limpeza Automática** (`cleanup_expired`)
- Executada automaticamente ao acessar a página de reservas
- Marca reservas expiradas como "expired"
- Libera o estoque automaticamente

### 4. Estados de uma Reserva

| Estado | Descrição | Ações Disponíveis |
|--------|-----------|-------------------|
| **Active** | Reserva ativa dentro do prazo | Confirmar, Cancelar, Estender |
| **Expired** | Prazo expirado (ainda não limpa) | Cancelar (remove) |
| **Confirmed** | Venda confirmada, estoque reduzido | Nenhuma (registro histórico) |
| **Cancelled** | Cancelada pelo admin | Nenhuma (registro histórico) |

### 5. Interface do Cliente

#### No Catálogo Público

Os produtos mostram status dinâmico:
- **"X available"**: Quantidade disponível (excluindo reservas)
- **"Last one!"**: Última unidade disponível
- **"Reserved"**: Todas unidades estão reservadas
- **Botão desabilitado**: Se não houver unidades disponíveis

#### No Carrinho

- Quantidade máxima ajustada automaticamente
- Validação ao tentar adicionar mais do que o disponível
- Mensagens claras sobre disponibilidade

## Integração com Django Admin

O modelo `StockReservation` está registrado no Django Admin com:

### Filtros e Busca
- Busca por nome do jogo, cliente ou email
- Filtros por status e data

### Ações em Lote
- Confirmar múltiplas reservas
- Cancelar múltiplas reservas
- Estender tempo de múltiplas reservas

### Campos de Visualização
- Lista: game, quantity, customer, status, created_at, expires_at, time_remaining
- Detalhes: todos os campos incluindo notas do admin

## Fluxo Completo de Exemplo

```
1. Cliente adiciona 2x "Catan" ao carrinho
   → Stock: 5, Disponível: 5

2. Cliente envia cotação
   → Sistema cria reserva de 2 unidades por 30 min
   → Stock: 5, Reservado: 2, Disponível: 3
   → Admin recebe email com ID da reserva

3. Outro cliente tenta adicionar ao carrinho
   → Máximo permitido: 3 unidades
   → Interface mostra "3 available"

4. Admin negocia com primeiro cliente
   → Opção A: Confirmar venda
     * Stock reduz para 3
     * Disponível: 3
     * Status: Confirmado
   
   → Opção B: Cliente desiste
     * Admin cancela reserva
     * Stock: 5, Disponível: 5
     * Status: Cancelado
   
   → Opção C: Precisa de mais tempo
     * Admin estende por +30 min
     * Reserva continua ativa

5. Se nada for feito em 30 min
   → Reserva expira automaticamente
   → Stock: 5, Disponível: 5
   → Status: Expirado
```

## Configuração

### Tempo de Expiração Padrão
Definido em `StockReservation.save()`:
```python
expires_at = timezone.now() + timezone.timedelta(minutes=30)
```

Para alterar, edite o valor de `minutes=30` no modelo.

### Limpeza Automática
Executada em:
- Ao acessar `/admin/reservations/`
- Pode ser executada via cron job:
```python
from catalog.models import StockReservation
StockReservation.cleanup_expired()
```

## URLs Disponíveis

| URL | Função |
|-----|--------|
| `/admin/reservations/` | Painel de gestão de reservas |
| `/admin/reservation/<id>/confirm/` | Confirmar venda |
| `/admin/reservation/<id>/cancel/` | Cancelar reserva |
| `/admin/reservation/<id>/extend/` | Estender tempo |

## Modelos de Dados

### StockReservation
```python
class StockReservation(models.Model):
    game = ForeignKey(BoardGame)
    quantity = IntegerField
    status = CharField  # active, confirmed, cancelled, expired
    customer_name = CharField
    customer_email = EmailField
    customer_phone = CharField
    customer_message = TextField
    session_key = CharField
    created_at = DateTimeField
    expires_at = DateTimeField
    confirmed_at = DateTimeField
    admin_notes = TextField
```

### Métodos Úteis
```python
# Verificar disponibilidade
game.available_quantity  # Considera reservas
game.is_available        # Bool: tem estoque disponível?
game.get_reserved_quantity()  # Total reservado

# Gerenciar reserva
reservation.confirm_sale(admin_notes="")
reservation.cancel_reservation(admin_notes="")
reservation.extend_reservation(minutes=30)
reservation.is_expired  # Bool
reservation.time_remaining  # TimeDelta

# Limpeza
StockReservation.cleanup_expired()  # Retorna count
```

## Benefícios

✅ **Evita vendas duplas**: Reserva temporária garante disponibilidade  
✅ **Melhor UX**: Cliente vê status real de disponibilidade  
✅ **Gestão eficiente**: Admin vê todas reservas pendentes em um lugar  
✅ **Flexível**: Pode estender, cancelar ou confirmar facilmente  
✅ **Automático**: Expira e libera estoque automaticamente  
✅ **Rastreável**: Histórico completo de todas reservas  
✅ **Integrado**: Funciona com carrinho e catálogo existentes  

## Próximos Passos Sugeridos

1. **Notificações por Email**:
   - Enviar email ao cliente quando reserva expira
   - Enviar email quando venda é confirmada

2. **Cron Job**:
   - Agendar limpeza automática de reservas expiradas
   - Ex: a cada 5 minutos

3. **Dashboard**:
   - Widget no admin panel mostrando reservas ativas
   - Gráficos de conversão (reservas → vendas)

4. **Relatórios**:
   - Taxa de conversão de reservas
   - Tempo médio até confirmação
   - Produtos mais reservados

5. **Melhorias UX**:
   - Contador regressivo para o cliente
   - Notificação push quando reserva está expirando
   - Sistema de prioridade (VIP reserva por mais tempo)
