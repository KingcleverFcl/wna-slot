# 🎰 wna-slot — Railway Edition

Простой слот на Flask. Вход по 64-значному коду. Подключение через Railway PostgreSQL.

## 🔐 Таблицы

**Casino** — игроки  
| id | code | balance |

**CC** — коды пополнения  
| code | amount | total_activation |

## 🚀 Деплой

1. Railway > New Project > Flask Template
2. Добавь PostgreSQL, привяжи к проекту.
3. Установи переменные:
   - `DATABASE_URL`
   - `SECRET_KEY`

## ✅ Использование

- Вставь в таблицу `cc` 64-значный код и настрой `amount` и `total_activation`.
- Пользователь вводит код, создаётся запись в `casino`, и он может играть.

## 🕹 Механика

- Стоимость спина: 10 монет
- Совпадение всех чисел в строке: +100
- Все числа одинаковы (мега-джекпот): +1000
