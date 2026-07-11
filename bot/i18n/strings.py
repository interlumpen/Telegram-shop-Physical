DEFAULT_LOCALE = "ru"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        # === Common Buttons ===
        "btn.shop": "🏪 Магазин",
        "btn.rules": "📜 Правила",
        "btn.profile": "👤 Профиль",
        "btn.support": "🆘 Поддержка",
        "btn.channel": "ℹ Новостной канал",
        "btn.admin_menu": "🎛 Панель администратора",
        "btn.back": "⬅️ Назад",
        "btn.close": "✖ Закрыть",
        "btn.yes": "✅ Да",
        "btn.no": "❌ Нет",
        "btn.check_subscription": "🔄 Проверить подписку",
        "btn.admin.ban_user": "🚫 Забанить пользователя",
        "btn.admin.unban_user": "✅ Разбанить пользователя",

        # === Admin Buttons (user management shortcuts) ===
        "btn.admin.promote": "⬆️ Назначить администратором",
        "btn.admin.demote": "⬇️ Снять администратора",
        "btn.admin.add_user_bonus": "🎁 Добавить реферальный бонус",

        # === Titles / Generic Texts ===
        "menu.title": "⛩️ Основное меню",
        "profile.caption": "👤 <b>Профиль</b> — <a href='tg://user?id={id}'>{name}</a>",
        "rules.not_set": "❌ Правила не были добавлены",
        "admin.users.cannot_ban_owner": "❌ Нельзя забанить владельца",
        "admin.users.ban.success": "✅ Пользователь {name} успешно забанен",
        "admin.users.ban.failed": "❌ Не удалось забанить пользователя",
        "admin.users.ban.notify": "⛔ Вы были забанены администратором",
        "admin.users.unban.success": "✅ Пользователь {name} успешно разбанен",
        "admin.users.unban.failed": "❌ Не удалось разбанить пользователя",
        "admin.users.unban.notify": "✅ Вы были разбанены администратором",

        # === Subscription Flow ===
        "subscribe.prompt": "Для начала подпишитесь на новостной канал",

        # === Profile ===
        "profile.referral_id": "👤 <b>Реферал</b> — <code>{id}</code>",
        "btn.referral": "🎲 Реферальная система",
        "btn.purchased": "🎁 Купленные товары",

        # === Profile Info Lines ===
        "profile.id": "🆔 <b>ID</b> — <code>{id}</code>",
        "profile.bonus_balance": "💰 <b>Реферальный бонус:</b> {bonus_balance} {currency}",
        "profile.purchased_count": "🎁 <b>Куплено товаров</b> — {count} шт",
        "profile.registration_date": "🕢 <b>Дата регистрации</b> — <code>{dt}</code>",

        # === Referral ===
        "referral.title": "💚 Реферальная система",
        "referral.count": "Количество рефералов: {count}",
        "referral.description": (
            "📔 Реферальная система позволит Вам заработать деньги без всяких вложений. "
            "Необходимо всего лишь распространять свою реферальную ссылку и Вы будете получать "
            "{percent}% от суммы пополнений Ваших рефералов на Ваш баланс бота."
        ),
        "btn.view_referrals": "👥 Мои рефералы",
        "btn.view_earnings": "💰 Мои поступления",

        "referrals.list.title": "👥 Ваши рефералы:",
        "referrals.list.empty": "У вас пока нет активных рефералов",
        "referrals.item.format": "ID: {telegram_id} | Принёс: {total_earned} {currency}",

        "referral.earnings.title": "💰 Поступления от реферала <code>{telegram_id}</code> (<a href='tg://user?id={telegram_id}'>{name}</a>):",
        "referral.earnings.empty": "От данного реферала <code>{id}</code> (<a href='tg://user?id={id}'>{name}</a>) пока не было поступлений",
        "referral.earning.format": "{amount} {currency} | {date} | (с {original_amount} {currency})",
        "referral.item.info": ("💰 Поступление номер: <code>{id}</code>\n"
                               "👤 Реферал: <code>{telegram_id}</code> (<a href='tg://user?id={telegram_id}'>{name}</a>)\n"
                               "🔢 Количество: {amount} {currency}\n"
                               "🕘 Дата: <code>{date}</code>\n"
                               "💵 С пополнения на {original_amount} {currency}"),

        "referral.admin_bonus.info": ("💰 Поступление номер: <code>{id}</code>\n"
                                      "🎁 <b>Бонус от администратора</b>\n"
                                      "🔢 Количество: {amount} {currency}\n"
                                      "🕘 Дата: <code>{date}</code>"),

        "all.earnings.title": "💰 Все ваши реферальные поступления:",
        "all.earnings.empty": "У вас пока нет реферальных поступлений",
        "all.earning.format.admin": "{amount} {currency} от Админа | {date}",

        "referrals.stats.template": (
            "📊 Статистика реферальной системы:\n\n"
            "👥 Активных рефералов: {active_count}\n"
            "💰 Всего заработано: {total_earned} {currency}\n"
            "📈 Общая сумма пополнений рефералов: {total_original} {currency}\n"
            "🔢 Количество начислений: {earnings_count}"
        ),

        # === Admin: Main Menu ===
        "admin.menu.main": "⛩️ Меню администратора",
        "admin.menu.shop": "🛒 Управление магазином",
        "admin.menu.goods": "📦 Управление позициями",
        "admin.menu.categories": "📂 Управление категориями",
        "admin.menu.users": "👥 Управление пользователями",
        "admin.menu.broadcast": "📝 Рассылка",
        "admin.menu.rights": "Недостаточно прав",

        # === Admin: User Management ===
        "admin.users.prompt_enter_id": "👤 Введите id пользователя,\nчтобы посмотреть | изменить его данные",
        "admin.users.invalid_id": "⚠️ Введите корректный числовой ID пользователя.",
        "admin.users.profile_unavailable": "❌ Профиль недоступен (такого пользователя никогда не существовало)",
        "admin.users.not_found": "❌ Пользователь не найден",
        "admin.users.cannot_change_owner": "Нельзя менять роль владельца",
        "admin.users.referrals": "👥 <b>Рефералы пользователя</b> — {count}",
        "admin.users.btn.view_referrals": "👥 Рефералы пользователя",
        "admin.users.btn.view_earnings": "💰 Поступления",
        "admin.users.role": "🎛 <b>Роль</b> — {role}",
        "admin.users.set_admin.success": "✅ Роль присвоена пользователю {name}",
        "admin.users.set_admin.notify": "✅ Вам присвоена роль АДМИНИСТРАТОРА бота",
        "admin.users.remove_admin.success": "✅ Роль отозвана у пользователя {name}",
        "admin.users.remove_admin.notify": "❌ У вас отозвана роль АДМИНИСТРАТОРА бота",
        "admin.users.bonus.prompt": "Введите сумму бонуса в {currency}:",
        "admin.users.bonus.added": "✅ Реферальный бонус пользователя {name} пополнен на {amount} {currency}",
        "admin.users.bonus.added.notify": "🎁 Вам начислен реферальный бонус на {amount} {currency}",
        "admin.users.bonus.invalid": "❌ Неверная сумма. Введите число от {min_amount} до {max_amount} {currency}.",

        # === Admin: Shop Management Menu ===
        "admin.shop.menu.title": "⛩️ Меню управления магазином",
        "admin.shop.menu.statistics": "📊 Статистика",
        "admin.shop.menu.logs": "📁 Показать логи",
        "admin.shop.menu.admins": "👮 Администраторы",
        "admin.shop.menu.users": "👤 Пользователи",

        # === Admin: Categories Management ===
        "admin.categories.menu.title": "⛩️ Меню управления категориями",
        "admin.categories.add": "➕ Добавить категорию",
        "admin.categories.rename": "✏️ Переименовать категорию",
        "admin.categories.delete": "🗑 Удалить категорию",
        "admin.categories.prompt.add": "Введите название новой категории:",
        "admin.categories.prompt.delete": "Введите название категории для удаления:",
        "admin.categories.prompt.rename.old": "Введите текущее название категории, которую нужно переименовать:",
        "admin.categories.prompt.rename.new": "Введите новое имя для категории:",
        "admin.categories.add.exist": "❌ Категория не создана (такая уже существует)",
        "admin.categories.add.success": "✅ Категория создана",
        "admin.categories.delete.not_found": "❌ Категория не удалена (такой категории не существует)",
        "admin.categories.delete.success": "✅ Категория удалена",
        "admin.categories.rename.not_found": "❌ Категория не может быть обновлена (такой категории не существует)",
        "admin.categories.rename.exist": "❌ Переименование невозможно (категория с таким именем уже существует)",
        "admin.categories.rename.success": "✅ Категория \"{old}\" переименована в \"{new}\"",

        # === Admin: Goods / Items Management (Add / List / Item Info) ===
        "admin.goods.add_position": "➕ Добавить позицию",
        "admin.goods.manage_stock": "➕ Добавить товар в позицию",
        "admin.goods.update_position": "📝 Изменить позицию",
        "admin.goods.delete_position": "❌ Удалить позицию",
        "admin.goods.add.prompt.name": "Введите название позиции",
        "admin.goods.add.name.exists": "❌ Позиция не может быть создана (такая позиция уже существует)",
        "admin.goods.add.prompt.description": "Введите описание для позиции:",
        "admin.goods.add.prompt.price": "Введите цену для позиции (число в {currency}):",
        "admin.goods.add.price.invalid": "⚠️ Некорректное значение цены. Введите число.",
        "admin.goods.add.prompt.category": "Введите категорию, к которой будет относиться позиция:",
        "admin.goods.add.category.not_found": "❌ Позиция не может быть создана (категория для привязки введена неверно)",
        "admin.goods.position.not_found": "❌ Товаров нет (Такой позиции не существует)",
        "admin.goods.menu.title": "⛩️ Меню управления позициями",
        "admin.goods.add.stock.prompt": "Введите количество товара для добавления",
        "admin.goods.add.stock.invalid": "⚠️ Некорректное значение количества товара. Введите число.",
        "admin.goods.add.stock.negative": "⚠️ Некорректное значение количества товара. Введите положительно число.",
        "admin.goods.add.result.created_with_stock": "✅ Позиция {item_name} создана, добавлено {stock_quantity} в количество товара.",

        # === Admin: Goods / Items Update Flow ===
        "admin.goods.update.position.invalid": "Позиция не найдена.",
        "admin.goods.update.position.exists": "Позиция с таким именем уже существует.",
        "admin.goods.update.prompt.name": "Введите название позиции",
        "admin.goods.update.not_exists": "❌ Позиция не может быть изменена (такой позиции не существует)",
        "admin.goods.update.prompt.new_name": "Введите новое имя для позиции:",
        "admin.goods.update.prompt.description": "Введите описание для позиции:",
        "admin.goods.update.success": "✅ Позиция обновлена",

        # === Admin: Goods / Items Delete Flow ===
        "admin.goods.delete.prompt.name": "Введите название позиции",
        "admin.goods.delete.position.not_found": "❌ Позиция не удалена (Такой позиции не существует)",
        "admin.goods.delete.position.success": "✅ Позиция удалена",

        # === Admin: Item Info ===
        "admin.goods.view_stock": "Посмотреть товары",
        "admin.goods.stock.status_title": "Статус товаров:",

        # === Admin: Logs ===
        "admin.shop.logs.caption": "Логи бота",
        "admin.shop.logs.empty": "❗️ Логов пока нет",

        # === Group Notifications ===
        "shop.group.new_upload": "Залив",
        "shop.group.item": "Товар",
        "shop.group.stock": "Количество",

        # === Admin: Statistics ===
        "admin.shop.stats.template": (
            "Статистика магазина:\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "<b>◽ПОЛЬЗОВАТЕЛИ</b>\n"
            "◾️Пользователей за 24 часа: {today_users}\n"
            "◾️Всего администраторов: {admins}\n"
            "◾️Всего пользователей: {users}\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "◽<b>СРЕДСТВА</b>\n"
            "◾Продаж за 24 часа на: {today_orders} {currency}\n"
            "◾Продано товаров на: {all_orders} {currency}\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "◽<b>ПРОЧЕЕ</b>\n"
            "◾Товаров: {items} шт.\n"
            "◾Позиций: {goods} шт.\n"
            "◾Категорий: {categories} шт.\n"
            "◾Продано товаров: {sold_count} шт."
        ),

        # === Admin: Lists & Broadcast ===
        "admin.shop.admins.title": "👮 Администраторы бота:",
        "admin.shop.users.title": "Пользователи бота:",
        "broadcast.prompt": "Отправьте сообщение для рассылки:",
        "broadcast.creating": "📤 Начинаем рассылку...\n👥 Всего пользователей: {ids}",
        "broadcast.progress": (
            "📤 Рассылка в процессе...\n\n"
            "📊 Прогресс: {progress:.1f}%\n"
            "✅ Отправлено: {sent}/{total}\n"
            "❌ Ошибок: {failed}\n"
            "⏱ Прошло времени: {time} сек"),
        "broadcast.done": (
            "✅ Рассылка завершена!\n\n"
            "📊 Статистика:\n"
            "👥 Всего: {total}\n"
            "✅ Доставлено: {sent}\n"
            "❌ Не доставлено: {failed}\n"
            "🚫 Заблокировали бота: ~{blocked}\n"
            "📈 Успешность: {success}%\n"
            "⏱ Время: {duration} сек"
        ),
        "broadcast.cancel": "❌ Рассылка отменена",
        "broadcast.warning": "Нет активной рассылки",

        # === Shop Browsing (Categories / Goods / Item Page) ===
        "shop.categories.title": "🏪 Категории магазина",
        "shop.goods.choose": "🏪 Выберите нужный товар",
        "shop.item.not_found": "Товар не найден",
        "shop.item.title": "🏪 Товар {name}",
        "shop.item.description": "Описание: {description}",
        "shop.item.price": "Цена — {amount} {currency}",
        "shop.item.quantity_unlimited": "Количество — неограниченно",
        "shop.item.quantity_left": "Количество — {count} шт.",
        "shop.item.quantity_detailed": "📦 Всего на складе: {total} шт.\n🔒 Зарезервировано: {reserved} шт.\n✅ Доступно для заказа: {available} шт.",

        # === Purchases ===
        "purchases.title": "Купленные товары:",
        "purchases.pagination.invalid": "Некорректные данные пагинации",
        "purchases.item.not_found": "Покупка не найдена",
        "purchases.item.name": "<b>🧾 Товар</b>: <code>{name}</code>",
        "purchases.item.price": "<b>💵 Цена</b>: <code>{amount}</code> {currency}",
        "purchases.item.datetime": "<b>🕒 Дата покупки</b>: <code>{dt}</code>",
        "purchases.item.unique_id": "<b>🧾 Уникальный ID</b>: <code>{uid}</code>",
        "purchases.item.value": "<b>🔑 Значение</b>:\n<code>{value}</code>",

        # === Middleware ===
        "middleware.ban": "⏳ Вы временно заблокированы. Подождите {time} секунд",
        "middleware.above_limits": "⚠️ Слишком много запросов! Вы временно заблокированы.",
        "middleware.waiting": "⏳ Подождите {time} секунд перед следующим действием.",
        "middleware.security.session_outdated": "⚠️ Сессия устарела. Пожалуйста, начните заново.",
        "middleware.security.invalid_data": "❌ Недопустимые данные",
        "middleware.security.blocked": "❌ Доступ заблокирован",
        "middleware.security.not_admin": "⛔ Недостаточно прав",
        "middleware.security.banned": "⛔ <b>Вы забанены</b>\n\nПричина: {reason}",
        "middleware.security.banned_no_reason": "⛔ <b>Вы забанены</b>\n\nОбратитесь к администратору для получения дополнительной информации.",
        "middleware.security.rate_limit": "⚠️ Слишком много запросов! Пожалуйста, подождите немного.",

        # === Errors ===
        "errors.not_subscribed": "Вы не подписались",
        "errors.pagination_invalid": "Некорректные данные пагинации",
        "errors.invalid_data": "❌ Неправильные данные",
        "errors.channel.telegram_not_found": "Я не могу писать в канал. Добавьте меня админом канала для заливов @{channel} с правом публиковать сообщения.",
        "errors.channel.telegram_forbidden_error": "Канал не найден. Проверьте username канала для заливов @{channel}.",
        "errors.channel.telegram_bad_request": "Не удалось отправить в канал для заливов: {e}",

        # === Orders ===
        "order.payment_method.choose": "💳 Выберите способ оплаты:",
        "order.payment_method.bitcoin": "💳 Bitcoin",
        "order.payment_method.cash": "💵 Оплата наличными при получении",
        "order.status.notify_order_confirmed": (
            "Заказ {order_code} подтвержден! 🎉\n\n"
            "Ваш заказ будет доставлен: {delivery_time}\n\n"
            "Товары:\n{items}\n\n"
            "Общая сумма: {total}\n\n"
            "Ожидайте доставку!"
        ),
        "order.status.notify_order_delivered": (
            "Заказ {order_code} доставлен! ✅\n\n"
            "Спасибо за покупку! Будем рады видеть вас снова! 🙏"
        ),
        "order.status.notify_order_modified": (
            "Order {order_code} modified by admin 📝\n\n"
            "Changes:\n{changes}\n\n"
            "New total: {total}"
        ),

        # === Additional Common Buttons ===
        "btn.cart": "🛒 Корзина",
        "btn.my_orders": "📦 Мои заказы",
        "btn.reference_codes": "🔑 Реферальные коды",
        "btn.settings": "⚙️ Настройки",
        "btn.referral_bonus_percent": "💰 Процент реферального бонуса",
        "btn.order_timeout": "⏱️ Таймаут заказа",
        "btn.timezone": "🌍 Часовой пояс",
        "btn.skip": "⏭️ Пропустить",
        "btn.use_saved_info": "✅ Использовать сохраненную информацию",
        "btn.update_info": "✏️ Обновить информацию",
        "btn.back_to_cart": "◀️ Назад к корзине",
        "btn.clear_cart": "🗑️ Очистить корзину",
        "btn.proceed_checkout": "💳 Перейти к оформлению",
        "btn.remove_item": "❌ Удалить {item_name}",
        "btn.use_all_bonus": "Использовать все {amount} {currency}",
        "btn.apply_bonus_yes": "✅ Да, применить бонус",
        "btn.apply_bonus_no": "❌ Нет, сохранить на потом",
        "btn.cancel": "❌ Отменить",
        "btn.add_to_cart": "🛒 Добавить в корзину",

        # === Cart Management ===
        "cart.add_success": "✅ {item_name} добавлен в корзину!",
        "cart.add_error": "❌ {message}",
        "cart.empty": "🛒 Ваша корзина пуста.\n\nПросмотрите магазин, чтобы добавить товары!",
        "cart.title": "🛒 <b>Ваша корзина покупок</b>\n\n",
        "cart.removed_success": "Товар удален из корзины",
        "cart.cleared_success": "✅ Корзина успешно очищена!",
        "cart.empty_alert": "Корзина пуста!",
        "cart.summary_title": "📦 <b>Сводка заказа</b>\n\n",
        "cart.saved_delivery_info": "Ваша сохраненная информация о доставке:\n\n",
        "cart.delivery_address": "📍 Адрес: {address}\n",
        "cart.delivery_phone": "📞 Телефон: {phone}\n",
        "cart.delivery_note": "📝 Примечание: {note}\n",
        "order.expired.bonus_refund_notification": (
            "⏱️ <b>Заказ истёк</b>\n\n"
            "Ваш заказ <b>{code}</b> истёк из-за истечения времени оплаты.\n\n"
            "💰 <b>Возврат бонуса: {bonus} {currency}</b>\n"
            "📊 Новый баланс бонусов: <b>{balance} {currency}</b>\n\n"
            "Ваш реферальный бонус возвращён на счёт.\n"
            "Вы можете использовать его для следующего заказа!"
        ),
        # === Reference Codes ===
        "refcode.type_admin": "Админ",
        "refcode.type_user": "Пользователь",
        "refcode.type_admin_emoji": "👑 Админ",
        "refcode.type_user_emoji": "👤 Пользователь",
        "refcode.status_active": "✅ Активен",
        "refcode.status_inactive": "❌ Неактивен",
        "refcode.never": "Никогда",
        "refcode.unlimited": "Без ограничений",
        "refcode.none_note": "Нет",
        "refcode.expires_hours": "{hours} ч.",
        "refcode.user.prompt_enter": "🔑 Пожалуйста, введите ваш реферальный код для доступа к магазину.\n\nЕсли у вас нет реферального кода, обратитесь к администратору.",
        "refcode.user.error_retry": "❌ {error}\n\nПопробуйте снова или обратитесь к администратору.",
        "refcode.user.welcome": "✅ Добро пожаловать! Ваш реферальный код подтверждён.\nТеперь у вас есть доступ к магазину.",
        "refcode.user.registration_cancelled": "Регистрация отменена. Отправьте /start, чтобы попробовать снова.",
        "refcode.user.my_none": "Вы ещё не создали ни одного реферального кода.\n\nПользователи могут создавать реферальные коды, действующие 24 часа и рассчитанные на 1 человека.",
        "refcode.user.my_title": "📋 Ваши реферальные коды:\n\n",
        "refcode.user.my_entry": "🔑 <code>{code}</code>\n   Тип: {type}\n   Использований: {current}/{max}\n   Истекает: {expires}\n   Статус: {status}\n\n",
        "refcode.user.create_existing": "ℹ️ У вас уже есть активный реферальный код:\n\n🔑 Код: <code>{code}</code>\n\n⏰ Истекает: {expires}\n👤 Использований: {current}/{max}\n\n💡 У вас может быть только один активный код одновременно.\nДождитесь, пока он истечёт или будет использован, прежде чем создавать новый.",
        "refcode.user.create_success": "✅ Ваш реферальный код создан!\n\n🔑 Код: <code>{code}</code>\n\n⏰ Действует: 24 часа\n👤 Может использовать: 1 человек\n\nПоделитесь этим кодом, чтобы пригласить кого-то в магазин!",
        "refcode.user.create_error": "❌ Ошибка при создании реферального кода: {error}",
        "refcode.admin.access_denied": "❌ Доступ запрещён",
        "refcode.admin.menu": "🔑 <b>Управление реферальными кодами</b>\n\nУправляйте реферальными кодами для контроля доступа к магазину.\n\nАдминские коды могут иметь настраиваемый срок действия и лимиты использования.",
        "refcode.admin.create_prompt_expires": "➕ <b>Создать реферальный код</b>\n\nВведите срок действия в часах:\n• Отправьте <code>0</code> для бессрочного\n• Отправьте <code>24</code> для 24 часов\n• Отправьте <code>168</code> для 1 недели\n\nИли нажмите «Назад» для отмены.",
        "refcode.admin.hours_positive": "❌ Часы должны быть положительными или 0 (без срока).",
        "refcode.admin.enter_valid_number": "❌ Пожалуйста, введите корректное число.",
        "refcode.admin.create_prompt_max_uses": "👥 <b>Максимум использований</b>\n\nВведите максимальное количество использований:\n• Отправьте <code>0</code> для неограниченного\n• Отправьте <code>1</code> для одноразового\n• Отправьте <code>10</code> для 10 использований\n\nИли нажмите «Назад» для отмены.",
        "refcode.admin.max_uses_positive": "❌ Максимум использований должен быть положительным или 0 (без ограничений).",
        "refcode.admin.create_prompt_note": "📝 <b>Необязательное примечание</b>\n\nВведите необязательное примечание для этого кода (например, «VIP-клиенты», «Маркетинговая кампания»):\n\n• Отправьте текст примечания\n• Или отправьте <code>skip</code>, чтобы пропустить\n\nИли нажмите «Назад» для отмены.",
        "refcode.admin.created": "✅ <b>Реферальный код создан!</b>\n\n🔑 Код: <code>{code}</code>\n\n⏰ Истекает через: {expires}\n👤 Макс. использований: {max_uses}\n📝 Примечание: {note}\n\nПоделитесь этим кодом для предоставления доступа к магазину.",
        "refcode.admin.create_error": "❌ Ошибка при создании кода: {error}",
        "refcode.admin.list_none": "ℹ️ Реферальные коды не найдены.",
        "refcode.admin.list_title": "📋 <b>Реферальные коды</b> (последние 20)\n\n",
        "refcode.admin.list_entry": "{status} <code>{code}</code> {type}\n   Использований: {current}/{max} | Истекает: {expires}\n",
        "refcode.admin.list_note": "   Примечание: {note}\n",
        "cart.use_info_question": "\n\nХотите использовать эту информацию или обновить ее?",
        "cart.no_saved_info": "❌ Сохраненная информация о доставке не найдена. Пожалуйста, введите вручную.",

        # === Order/Delivery Flow ===
        "order.delivery.address_prompt": "📍 Пожалуйста, введите ваш адрес доставки:",
        "order.delivery.address_invalid": "❌ Пожалуйста, укажите действительный адрес доставки (минимум 5 символов).",
        "order.delivery.phone_prompt": "📞 Пожалуйста, введите ваш номер телефона (с кодом страны):",
        "order.delivery.phone_invalid": "❌ Пожалуйста, укажите действительный номер телефона (минимум 8 цифр).",
        "order.delivery.note_prompt": "📝 Есть ли какие-то особые инструкции по доставке? (Необязательно)\n\nВы можете пропустить это, нажав на кнопку ниже.",
        "order.delivery.info_save_error": "❌ Ошибка сохранения информации о доставке. Пожалуйста, попробуйте еще раз.",

        # === Bonus/Referral Application ===
        "order.bonus.available": "💰 <b>У вас есть {bonus_balance} {currency} в реферальных бонусах!</b>\n\n",
        "order.bonus.apply_question": "Хотите ли вы применить реферальный бонус к этому заказу?",
        "order.bonus.amount_positive_error": "❌ Пожалуйста, введите положительную сумму.",
        "order.bonus.amount_too_high": "❌ Сумма слишком велика. Максимум применимо: {max_applicable} {currency}\nПожалуйста, введите корректную сумму:",
        "order.bonus.invalid_amount": "❌ Неверная сумма. Пожалуйста, введите число (например, 5.50):",
        "order.bonus.insufficient": "❌ Недостаточный бонусный баланс. Пожалуйста, попробуйте снова.",
        "order.bonus.enter_amount": "Введите сумму бонуса, которую вы хотите применить (максимум {max_applicable} {currency}):\n\nИли используйте все доступные бонусы, нажав кнопку ниже.",

        # === Payment Instructions ===
        "order.payment.system_unavailable": "❌ <b>Платежная система временно недоступна</b>\n\nНет доступных Bitcoin-адресов. Пожалуйста, свяжитесь с поддержкой.",
        "order.payment.customer_not_found": "❌ Информация о клиенте не найдена. Пожалуйста, попробуйте снова.",
        "order.payment.creation_error": "❌ Ошибка создания заказов. Пожалуйста, попробуйте снова или свяжитесь с поддержкой.",

        # === Order Summary/Total ===
        "order.summary.title": "📦 <b>Сводка заказа</b>\n\n",
        "order.summary.cart_total": "Итого корзины: {cart_total} {currency}",
        "order.summary.bonus_applied": "Применен бонус: -{bonus_applied} {currency}",
        "order.summary.final_amount": "Итоговая сумма: {final_amount} {currency}",

        # === Inventory/Reservation ===
        "order.inventory.unable_to_reserve": "❌ <b>Не удается зарезервировать товары</b>\n\nСледующие товары недоступны в запрошенных количествах:\n\n{unavailable_items}\n\nПожалуйста, скорректируйте вашу корзину и попробуйте снова.",

        # === My Orders View ===
        "myorders.title": "📦 <b>Мои заказы</b>\n\n",
        "myorders.total": "Всего заказов: {count}",
        "myorders.active": "⏳ Активных заказов: {count}",
        "myorders.delivered": "✅ Доставлено: {count}",
        "myorders.select_category": "Выберите категорию для просмотра заказов:",
        "myorders.active_orders": "⏳ Активные заказы",
        "myorders.delivered_orders": "✅ Доставленные заказы",
        "myorders.all_orders": "📋 Все заказы",
        "myorders.no_orders_yet": "Вы еще не сделали ни одного заказа.\n\nПросмотрите магазин, чтобы начать делать покупки!",
        "myorders.browse_shop": "🛍️ Перейти в магазин",
        "myorders.back": "◀️ Назад",
        "myorders.all_title": "📋 Все заказы",
        "myorders.active_title": "⏳ Активные заказы",
        "myorders.delivered_title": "✅ Доставленные заказы",
        "myorders.invalid_filter": "Неверный фильтр",
        "myorders.not_found": "Заказы не найдены.",
        "myorders.back_to_menu": "◀️ Назад к меню заказов",
        "myorders.select_details": "Выберите заказ для просмотра деталей:",
        "myorders.order_not_found": "Заказ не найден",

        # === Order Details Display ===
        "myorders.detail.title": "📦 <b>Детали заказа #{order_code}</b>\n\n",
        "myorders.detail.status": "📊 <b>Статус:</b> {status}\n",
        "myorders.detail.subtotal": "💵 <b>Подытог:</b> {subtotal} {currency}\n",
        "myorders.detail.bonus_applied": "🎁 <b>Применен бонус:</b> {bonus} {currency}\n",
        "myorders.detail.final_price": "💰 <b>Итоговая цена:</b> {total} {currency}\n",
        "myorders.detail.total_price": "💰 <b>Итоговая цена:</b> {total} {currency}\n",
        "myorders.detail.payment_method": "💳 <b>Способ оплаты:</b> {method}\n",
        "myorders.detail.ordered": "📅 <b>Заказано:</b> {date}\n",
        "myorders.detail.delivery_time": "🚚 <b>Запланированная доставка:</b> {time}\n",
        "myorders.detail.completed": "✅ <b>Завершено:</b> {date}\n",
        "myorders.detail.items": "\n📦 <b>Товары:</b>\n{items}\n",
        "myorders.detail.delivery_info": "\n📍 <b>Информация о доставке:</b>\n{address}\n{phone}\n{note}",

        # === Help System ===
        "help.prompt": "📧 <b>Нужна помощь?</b>\n\n",
        "help.describe_issue": "Пожалуйста, опишите вашу проблему или вопрос, и он будет отправлен напрямую администратору.\n\nВведите ваше сообщение ниже:",
        "help.admin_not_configured": "❌ Извините, контакт администратора не настроен. Пожалуйста, попробуйте позже.",
        "help.admin_notification_title": "📧 <b>Новый запрос помощи</b>\n\n",
        "help.admin_notification_from": "<b>От:</b> @{username} (ID: {user_id})\n",
        "help.admin_notification_message": "<b>Сообщение:</b>\n{message}",
        "help.sent_success": "✅ {auto_message}",
        "help.sent_error": "❌ Не удалось отправить сообщение администратору: {error}\n\nПожалуйста, попробуйте позже.",
        "help.cancelled": "Запрос помощи отменен.",

        # === Admin Order Notifications ===
        "admin.goods.add.stock.error": "❌ Ошибка при добавлении начального запаса: {error}",
        "admin.order.action_required_title": "⏳ <b>Требуется действие:</b>",
        "admin.order.address_label": "Адрес: {address}",
        "admin.order.amount_to_collect_label": "<b>Сумма к получению: {amount} {currency}</b>",
        "admin.order.amount_to_receive_label": "<b>Сумма к получению: {amount} {currency}</b>",
        "admin.order.awaiting_payment_status": "⏳ Ожидание подтверждения оплаты...",
        "admin.order.bitcoin_address_label": "Bitcoin адрес: <code>{address}</code>",
        "admin.order.bonus_applied_label": "Применён бонус: <b>-{amount} {currency}</b>",
        "admin.order.customer_label": "Покупатель: {username} (ID: {id})",
        "admin.order.delivery_info_title": "<b>Информация о доставке:</b>",
        "admin.order.items_title": "<b>Товары:</b>",
        "admin.order.new_bitcoin_order": "🔔 <b>Новый BITCOIN заказ получен</b>",
        "admin.order.new_cash_order": "🔔 <b>Новый НАЛИЧНЫЙ заказ получен</b> 💵",
        "admin.order.note_label": "Примечание: {note}",
        "admin.order.order_label": "Заказ: <b>{code}</b>",
        "admin.order.payment_cash": "Наличными при доставке",
        "admin.order.payment_header": "\n<b>Оплата:</b>\n",
        "admin.order.payment_method_label": "Способ оплаты: <b>{method}</b>",
        "admin.order.phone_label": "Телефон: {phone}",
        "admin.order.subtotal_label": "Подытог: <b>{amount} {currency}</b>",
        "admin.order.total_label": "<b>Итого: {amount} {currency}</b>\n\n",
        "admin.order.use_cli_confirm": "Используйте CLI для подтверждения заказа и установки времени доставки:\n<code>python bot_cli.py order --order-code {code} --status-confirmed --delivery-time \"YYYY-MM-DD HH:MM\"</code>",
        "btn.admin.back_to_panel": "🔙 Назад в панель администратора",
        "btn.admin.create_refcode": "➕ Создать реферальный код",
        "btn.admin.list_refcodes": "📋 Список всех кодов",
        "btn.back_to_orders": "◀️ Назад к заказам",
        "btn.create_reference_code": "➕ Создать реферальный код",
        "btn.my_reference_codes": "🔑 Мои реферальные коды",
        "btn.need_help": "❓ Нужна помощь?",
        "cart.item.price_format": "  Цена: {price} {currency} × {quantity}",
        "cart.item.subtotal_format": "  Подытог: {subtotal} {currency}",
        "cart.total_format": "<b>Итого: {total} {currency}</b>",
        "help.pending_order.contact_support": "Используйте команду /help для связи с поддержкой.",
        "help.pending_order.issues_title": "<b>Возникли проблемы?</b>",
        "help.pending_order.status": "Ваш заказ в настоящее время ожидает оплаты.",
        "help.pending_order.step1": "1. Отправьте точную сумму на указанный Bitcoin адрес",
        "help.pending_order.step2": "2. Дождитесь подтверждения в блокчейне (обычно 10-60 минут)",
        "help.pending_order.step3": "3. Администратор подтвердит оплату и назначит время доставки",
        "help.pending_order.step4": "4. Ваши товары будут доставлены курьером.",
        "help.pending_order.title": "❓ <b>Нужна помощь с заказом?</b>",
        "help.pending_order.what_to_do_title": "<b>Что делать:</b>",
        "myorders.detail.bitcoin_address_label": "Bitcoin адрес:",
        "myorders.detail.bitcoin_admin_confirm": "После оплаты администратор подтвердит ваш заказ.",
        "myorders.detail.bitcoin_send_instruction": "⚠️ Пожалуйста, отправьте <b>{amount} {currency}</b> Bitcoin на этот адрес.",
        "myorders.detail.cash_awaiting_confirm": "Ваш заказ ожидает подтверждения администратора.",
        "myorders.detail.cash_payment_courier": "Оплата будет произведена курьеру при доставке.",
        "myorders.detail.cash_title": "💵 Оплата при доставке",
        "myorders.detail.cash_will_notify": "Вы будете уведомлены, когда заказ будет подтвержден и установлено время доставки.",
        "myorders.detail.confirmed_title": "✅ <b>Заказ подтвержден!</b>",
        "myorders.detail.delivered_thanks_message": "Спасибо за покупку! Надеемся увидеть вас снова! 🙏",
        "myorders.detail.delivered_title": "📦 <b>Заказ доставлен!</b>",
        "myorders.detail.payment_info_title": "<b>Информация об оплате:</b>",
        "myorders.detail.preparing_message": "Ваш заказ готовится к доставке.",
        "myorders.detail.scheduled_delivery_label": "Запланированная доставка: <b>{time}</b>",
        "myorders.order_summary_format": "{status_emoji} {code} - {items_count} товаров - {total} {currency}",
        "order.bonus.available_label": "Доступный бонус: <b>{amount} {currency}</b>",
        "order.bonus.choose_amount_hint": "Вы можете выбрать сколько использовать (до {max_amount} {currency})",
        "order.bonus.enter_amount_title": "💵 <b>Введите сумму бонуса для применения</b>",
        "order.bonus.max_applicable_label": "Максимум применимо: <b>{amount} {currency}</b>",
        "order.bonus.order_total_label": "Сумма заказа: <b>{amount} {currency}</b>",
        "order.info.view_status_hint": "💡 Вы можете просмотреть статус заказа в любое время, используя команду /orders.",
        "order.payment.bitcoin.address_title": "<b>Bitcoin адрес для оплаты:</b>",
        "order.payment.bitcoin.admin_confirm": "• После оплаты администратор подтвердит ваш заказ",
        "order.payment.bitcoin.delivery_title": "<b>Доставка:</b>",
        "order.payment.bitcoin.important_title": "⚠️ <b>ВАЖНО:</b>",
        "order.payment.bitcoin.items_title": "<b>Товары:</b>",
        "order.payment.bitcoin.need_help": "Нужна помощь? Используйте /help для связи с поддержкой.",
        "order.payment.bitcoin.one_time_address": "• Этот адрес для ОДНОРАЗОВОГО использования",
        "order.payment.bitcoin.order_code": "Заказ: <b>{code}</b>",
        "order.payment.bitcoin.send_exact": "• Отправьте ТОЧНУЮ сумму, указанную выше",
        "order.payment.bitcoin.title": "💳 <b>Инструкции по оплате Bitcoin</b>",
        "order.payment.bitcoin.total_amount": "Сумма к оплате: <b>{amount} {currency}</b>",
        "order.payment.cash.admin_contact": "Администратор свяжется с вами в ближайшее время.",
        "order.payment.cash.after_confirm": "После подтверждения вы будете уведомлены о времени доставки.",
        "order.payment.cash.created": "Ваш заказ {code} создан и ожидает подтверждения администратора.",
        "order.payment.cash.important": "⏳ <b>Важно:</b> Заказ зарезервирован на ограниченное время.",
        "order.payment.cash.items_title": "Товары:",
        "order.payment.cash.payment_to_courier": "Оплата будет произведена курьеру при доставке.",
        "order.payment.cash.title": "💵 <b>Оплата при доставке</b>",
        "order.payment.cash.total": "Итого: {amount}",
        "order.payment.error_general": "❌ Ошибка создания заказа. Попробуйте снова или обратитесь в поддержку.",
        "order.summary.total_label": "<b>Итого: {amount} {currency}</b>",
        "order.payment.bonus_applied_label": "Применён бонус: <b>-{amount} {currency}</b>",
        "order.payment.cash.amount_with_bonus": "<b>Сумма к оплате при доставке: {amount} {currency}</b>",
        "order.payment.cash.total_label": "<b>Итого к оплате при доставке: {amount} {currency}</b>",
        "order.payment.final_amount_label": "<b>Итоговая сумма к оплате: {amount} {currency}</b>",
        "order.payment.order_label": "📋 <b>Заказ: {code}</b>",
        "order.payment.subtotal_label": "Подытог: <b>{amount} {currency}</b>",
        "order.payment.total_amount_label": "<b>Сумма к оплате: {amount} {currency}</b>",
    },

    "en": {
        # === Common Buttons ===
        "btn.shop": "🏪 Shop",
        "btn.rules": "📜 Rules",
        "btn.profile": "👤 Profile",
        "btn.support": "🆘 Support",
        "btn.channel": "ℹ News channel",
        "btn.admin_menu": "🎛 Admin panel",
        "btn.back": "⬅️ Back",
        "btn.close": "✖ Close",
        "btn.yes": "✅ Yes",
        "btn.no": "❌ No",
        "btn.check_subscription": "🔄 Check subscription",
        "btn.admin.ban_user": "🚫 Ban user",
        "btn.admin.unban_user": "✅ Unban user",

        # === Admin Buttons (user management shortcuts) ===
        "btn.admin.promote": "⬆️ Make admin",
        "btn.admin.demote": "⬇️ Remove admin",
        "btn.admin.add_user_bonus": "🎁 Add referral bonus",

        # === Titles / Generic Texts ===
        "menu.title": "⛩️ Main menu",
        "admin.goods.add.stock.error": "❌ Error adding initial stock: {error}",
        "admin.goods.stock.add_success": "✅ Added {quantity} units to \"{item}\"",
        "admin.goods.stock.add_units": "➕ Add units",
        "admin.goods.stock.current_status": "Current Status",
        "admin.goods.stock.error": "❌ Error managing stock: {error}",
        "admin.goods.stock.insufficient": "❌ Insufficient stock. Only {available} units available.",
        "admin.goods.stock.invalid_quantity": "⚠️ Invalid quantity. Enter a whole number.",
        "admin.goods.stock.management_title": "Stock Management: {item}",
        "admin.goods.stock.negative_quantity": "⚠️ Quantity cannot be negative.",
        "admin.goods.stock.no_products": "❌ No products in the shop yet",
        "admin.goods.stock.prompt.add_units": "Enter the number of units to add:",
        "admin.goods.stock.prompt.item_name": "Enter the product name to manage stock:",
        "admin.goods.stock.prompt.remove_units": "Enter the number of units to remove:",
        "admin.goods.stock.prompt.set_exact": "Enter the exact stock quantity:",
        "admin.goods.stock.redirect_message": "ℹ️ Stock management is now available through the \"Manage Stock\" menu",
        "admin.goods.stock.remove_success": "✅ Removed {quantity} units from \"{item}\"",
        "admin.goods.stock.remove_units": "➖ Remove units",
        "admin.goods.stock.select_action": "Select action",
        "admin.goods.stock.set_exact": "⚖️ Set exact quantity",
        "admin.goods.stock.set_success": "✅ Stock for \"{item}\" set to {quantity} units",
        "admin.goods.stock.status_title": "📊 Stock Status:",
        "errors.invalid_item_name": "❌ Invalid item name",
        "profile.caption": "👤 <b>Profile</b> — <a href='tg://user?id={id}'>{name}</a>",
        "rules.not_set": "❌ Rules have not been added",
        "admin.users.cannot_ban_owner": "❌ Cannot ban the owner",
        "admin.users.ban.success": "✅ User {name} has been successfully banned",
        "admin.users.ban.failed": "❌ Failed to ban user",
        "admin.users.ban.notify": "⛔ You have been banned by an administrator",
        "admin.users.unban.success": "✅ User {name} has been successfully unbanned",
        "admin.users.unban.failed": "❌ Failed to unban user",
        "admin.users.unban.notify": "✅ You have been unbanned by an administrator",

        # === Profile ===
        "btn.referral": "🎲 Referral system",
        "btn.purchased": "🎁 Purchased goods",
        "profile.referral_id": "👤 <b>Referral</b> — <code>{id}</code>",

        # === Subscription Flow ===
        "subscribe.prompt": "First, subscribe to the news channel",

        # === Profile Info Lines ===
        "profile.id": "🆔 <b>ID</b> — <code>{id}</code>",
        "profile.bonus_balance": "💰 <b>Referral Bonus:</b> {bonus_balance} {currency}",
        "profile.purchased_count": "🎁 <b>Purchased items</b> — {count} pcs",
        "profile.registration_date": "🕢 <b>Registered at</b> — <code>{dt}</code>",

        # === Referral ===
        "referral.title": "💚 Referral system",
        "referral.count": "Referrals count: {count}",
        "referral.description": (
            "📔 The referral system lets you earn without any investment. "
            "Share your personal link and you will receive {percent}% of your referrals’ "
            "top-ups to your bot balance."
        ),
        "btn.view_referrals": "👥 My referrals",
        "btn.view_earnings": "💰 My earnings",

        "referrals.list.title": "👥 Your referrals:",
        "referrals.list.empty": "You don't have any active referrals yet",
        "referrals.item.format": "ID: {telegram_id} | Earned: {total_earned} {currency}",

        "referral.earnings.title": "💰 Earnings from referral <code>{telegram_id}</code> (<a href='tg://user?id={telegram_id}'>{name}</a>):",
        "referral.earnings.empty": "No earnings from this referral <code>{id}</code> (<a href='tg://user?id={id}'>{name}</a>) yet",
        "referral.earning.format": "{amount} {currency} | {date} | (from {original_amount} {currency})",
        "referral.item.info": ("💰 Earning number: <code>{id}</code>\n"
                               "👤 Referral: <code>{telegram_id}</code> (<a href='tg://user?id={telegram_id}'>{name}</a>)\n"
                               "🔢 Amount: {amount} {currency}\n"
                               "🕘 Date: <code>{date}</code>\n"
                               "💵 From a deposit to {original_amount} {currency}"),

        "referral.admin_bonus.info": ("💰 Earning number: <code>{id}</code>\n"
                                      "🎁 <b>Bonus from administrator</b>\n"
                                      "🔢 Amount: {amount} {currency}\n"
                                      "🕘 Date: <code>{date}</code>"),

        "all.earnings.title": "💰 All your referral earnings:",
        "all.earnings.empty": "You have no referral earnings yet",
        "all.earning.format.admin": "{amount} {currency} from Admin | {date}",

        "referrals.stats.template": (
            "📊 Referral system statistics:\n\n"
            "👥 Active referrals: {active_count}\n"
            "💰 Total earned: {total_earned} {currency}\n"
            "📈 Total referrals top-ups: {total_original} {currency}\n"
            "🔢 Number of earnings: {earnings_count}"
        ),

        # === Admin: Main Menu ===
        "admin.menu.main": "⛩️ Admin Menu",
        "admin.menu.shop": "🛒 Shop management",
        "admin.menu.goods": "📦 Items management",
        "admin.menu.categories": "📂 Categories management",
        "admin.menu.users": "👥 Users management",
        "admin.menu.broadcast": "📝 Broadcast",
        "admin.menu.rights": "Insufficient permissions",

        # === Admin: User Management ===
        "admin.users.prompt_enter_id": "👤 Enter the user ID to view / edit data",
        "admin.users.invalid_id": "⚠️ Please enter a valid numeric user ID.",
        "admin.users.profile_unavailable": "❌ Profile unavailable (such user never existed)",
        "admin.users.not_found": "❌ User not found",
        "admin.users.cannot_change_owner": "You cannot change the owner’s role",
        "admin.users.referrals": "👥 <b>User referrals</b> — {count}",
        "admin.users.btn.view_referrals": "👥 User's referrals",
        "admin.users.btn.view_earnings": "💰 User's earnings",
        "admin.users.role": "🎛 <b>Role</b> — {role}",
        "admin.users.set_admin.success": "✅ Role assigned to {name}",
        "admin.users.set_admin.notify": "✅ You have been granted the ADMIN role",
        "admin.users.remove_admin.success": "✅ Admin role revoked from {name}",
        "admin.users.remove_admin.notify": "❌ Your ADMIN role has been revoked",
        "admin.users.bonus.prompt": "Enter bonus amount in {currency}:",
        "admin.users.bonus.added": "✅ {name}'s referral bonus has been topped up by {amount} {currency}",
        "admin.users.bonus.added.notify": "🎁 You have been credited with a referral bonus of {amount} {currency}",
        "admin.users.bonus.invalid": "❌ Invalid amount. Enter a number from {min_amount} to {max_amount} {currency}.",

        # === Admin: Shop Management Menu ===
        "admin.shop.menu.title": "⛩️ Shop management",
        "admin.shop.menu.statistics": "📊 Statistics",
        "admin.shop.menu.logs": "📁 Show logs",
        "admin.shop.menu.admins": "👮 Admins",
        "admin.shop.menu.users": "👤 Users",

        # === Admin: Categories Management ===
        "admin.categories.menu.title": "⛩️ Categories management",
        "admin.categories.add": "➕ Add category",
        "admin.categories.rename": "✏️ Rename category",
        "admin.categories.delete": "🗑 Delete category",
        "admin.categories.prompt.add": "Enter a new category name:",
        "admin.categories.prompt.delete": "Enter the category name to delete:",
        "admin.categories.prompt.rename.old": "Enter the current category name to rename:",
        "admin.categories.prompt.rename.new": "Enter the new category name:",
        "admin.categories.add.exist": "❌ Category not created (already exists)",
        "admin.categories.add.success": "✅ Category created",
        "admin.categories.delete.not_found": "❌ Category not deleted (does not exist)",
        "admin.categories.delete.success": "✅ Category deleted",
        "admin.categories.rename.not_found": "❌ Category cannot be updated (does not exist)",
        "admin.categories.rename.exist": "❌ Cannot rename (a category with this name already exists)",
        "admin.categories.rename.success": "✅ Category \"{old}\" renamed to \"{new}\"",

        # === Admin: Goods / Items Management (Add / List / Item Info) ===
        "admin.goods.add_position": "➕ add item",
        "admin.goods.manage_stock": "➕ Add product to item",
        "admin.goods.update_position": "📝 change item",
        "admin.goods.delete_position": "❌ delete item",
        "admin.goods.add.prompt.name": "Enter the item name",
        "admin.goods.add.name.exists": "❌ Item cannot be created (it already exists)",
        "admin.goods.add.prompt.description": "Enter item description:",
        "admin.goods.add.prompt.price": "Enter item price (number in {currency}):",
        "admin.goods.add.price.invalid": "⚠️ Invalid price. Please enter a number.",
        "admin.goods.add.prompt.category": "Enter the category the item belongs to:",
        "admin.goods.add.category.not_found": "❌ Item cannot be created (invalid category provided)",
        "admin.goods.position.not_found": "❌ No goods (this item doesn't exist)",
        "admin.goods.menu.title": "⛩️ Items management menu",
        "admin.goods.add.stock.prompt": "Enter the quantity of goods to add",
        "admin.goods.add.stock.invalid": "⚠️ Incorrect quantity value. Please enter a number.",
        "admin.goods.add.stock.negative": "⚠️ Incorrect quantity value. Enter a positive number.",
        "admin.goods.add.result.created_with_stock": "✅ Item {item_name} created, {stock_quantity} added to the quantity of goods.",

        # === Admin: Goods / Items Update Flow ===
        "admin.goods.update.position.invalid": "Item not found.",
        "admin.goods.update.position.exists": "An item with this name already exists.",
        "admin.goods.update.prompt.name": "Enter the item name",
        "admin.goods.update.not_exists": "❌ Item cannot be updated (does not exist)",
        "admin.goods.update.prompt.new_name": "Enter a new item name:",
        "admin.goods.update.prompt.description": "Enter item description:",
        "admin.goods.update.success": "✅ Item updated",

        # === Admin: Goods / Items Delete Flow ===
        "admin.goods.delete.prompt.name": "Enter the item name",
        "admin.goods.delete.position.not_found": "❌ item not deleted (this item doesn't exist)",
        "admin.goods.delete.position.success": "✅ item deleted",

        # === Admin: Item Info ===
        "admin.goods.view_stock": "View items",

        # === Admin: Logs ===
        "admin.shop.logs.caption": "Bot logs",
        "admin.shop.logs.empty": "❗️ No logs yet",

        # === Group Notifications ===
        "shop.group.new_upload": "New stock",
        "shop.group.item": "Item",
        "shop.group.stock": "Quantity",

        # === Admin: Statistics ===
        "admin.shop.stats.template": (
            "Shop statistics:\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "<b>◽USERS</b>\n"
            "◾️Users in last 24h: {today_users}\n"
            "◾️Total admins: {admins}\n"
            "◾️Total users: {users}\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "◽<b>MISC</b>\n"
            "◾Items: {items} pcs\n"
            "◾Positions: {goods} pcs\n"
            "◾Categories: {categories} pcs\n"
        ),

        # === Admin: Lists & Broadcast ===
        "admin.shop.admins.title": "👮 Bot admins:",
        "admin.shop.users.title": "Bot users:",
        "broadcast.prompt": "Send a message to broadcast:",
        "broadcast.creating": "📤 Starting the newsletter...\n👥 Total users: {ids}",
        "broadcast.progress": (
            "📤 Broadcasting in progress...\n\n\n"
            "📊 Progress: {progress:.1f}%{n}"
            "✅ Sent: {sent}/{total}\n"
            "❌ Errors: {failed}\n"
            "⏱ Time elapsed: {time} sec"),
        "broadcast.done": (
            "✅ Broadcasting is complete! \n\n"
            "📊 Statistics:📊\n"
            "👥 Total: {total}\n"
            "✅ Delivered: {sent}\n"
            "❌ Undelivered: {failed}\n"
            "🚫 Blocked bot: ~{blocked}\n"
            "📈 Success rate: {success}%\n"
            "⏱ Time: {duration} sec"
        ),
        "broadcast.cancel": "❌ The broadcast has been canceled.",
        "broadcast.warning": "No active broadcast",

        # === Shop Browsing (Categories / Goods / Item Page) ===
        "shop.categories.title": "🏪 Shop categories",
        "shop.goods.choose": "🏪 Choose a product",
        "shop.item.not_found": "Item not found",
        "shop.item.title": "🏪 Item {name}",
        "shop.item.description": "Description: {description}",
        "shop.item.price": "Price — {amount} {currency}",
        "shop.item.quantity_unlimited": "Quantity — unlimited",
        "shop.item.quantity_left": "Quantity — {count} pcs",
        "shop.item.quantity_detailed": "📦 Total in stock: {total} pcs\n🔒 Reserved: {reserved} pcs\n✅ Available to order: {available} pcs",

        # === Purchases ===
        "purchases.title": "Purchased items:",
        "purchases.pagination.invalid": "Invalid pagination data",
        "purchases.item.not_found": "Purchase not found",
        "purchases.item.name": "<b>🧾 Item</b>: <code>{name}</code>",
        "purchases.item.price": "<b>💵 Price</b>: <code>{amount}</code> {currency}",
        "purchases.item.datetime": "<b>🕒 Purchased at</b>: <code>{dt}</code>",
        "purchases.item.unique_id": "<b>🧾 Unique ID</b>: <code>{uid}</code>",
        "purchases.item.value": "<b>🔑 Value</b>:\n<code>{value}</code>",

        # === Middleware ===
        "middleware.ban": "⏳ You are temporarily blocked. Wait {time} seconds.",
        "middleware.above_limits": "⚠️ Too many requests! You are temporarily blocked.",
        "middleware.waiting": "⏳ Wait {time} seconds for the next action.",
        "middleware.security.session_outdated": "⚠️ Session is outdated. Please start again.",
        "middleware.security.invalid_data": "❌ Invalid data",
        "middleware.security.blocked": "❌ Access blocked",
        "middleware.security.not_admin": "⛔ Insufficient permissions",
        "middleware.security.banned": "⛔ <b>You have been banned</b>\n\nReason: {reason}",
        "middleware.security.banned_no_reason": "⛔ <b>You have been banned</b>\n\nPlease contact the administrator for more information.",
        "middleware.security.rate_limit": "⚠️ Too many requests! Please wait a moment.",

        # === Errors ===
        "errors.not_subscribed": "You are not subscribed",
        "errors.pagination_invalid": "Invalid pagination data",
        "errors.invalid_data": "❌ Invalid data",
        "errors.channel.telegram_not_found": "I can't write to the channel. Add me as a channel admin for uploads @{channel} with the right to publish messages.",
        "errors.channel.telegram_forbidden_error": "Channel not found. Check the channel username for uploads @{channel}.",
        "errors.channel.telegram_bad_request": "Failed to send to the channel for uploads: {e}",

        # === Orders ===
        "order.payment_method.choose": "💳 Choose payment method:",
        "order.payment_method.bitcoin": "💳 Bitcoin",
        "order.payment_method.cash": "💵 Cash on Delivery",
        "order.status.notify_order_confirmed": (
            "Order {order_code} confirmed! 🎉\n\n"
            "Your order will be delivered at: {delivery_time}\n\n"
            "Items:\n{items}\n\n"
            "Total: {total}\n\n"
            "Wait for delivery!"
        ),
        "order.status.notify_order_delivered": (
            "Order {order_code} delivered! ✅\n\n"
            "Thank you for your purchase! We look forward to seeing you again! 🙏"
        ),
        "order.status.notify_order_modified": (
            "Order {order_code} modified by admin 📝\n\n"
            "Changes:\n{changes}\n\n"
            "New total: {total}"
        ),

        # === Additional Common Buttons ===
        "btn.cart": "🛒 Cart",
        "btn.my_orders": "📦 My Orders",
        "btn.reference_codes": "🔑 Reference Codes",
        "btn.settings": "⚙️ Settings",
        "btn.referral_bonus_percent": "💰 Referral Bonus %",
        "btn.order_timeout": "⏱️ Order Timeout",
        "btn.timezone": "🌍 Timezone",
        "btn.skip": "⏭️ Skip",
        "btn.use_saved_info": "✅ Use Saved Info",
        "btn.update_info": "✏️ Update Info",
        "btn.back_to_cart": "◀️ Back to Cart",
        "btn.clear_cart": "🗑️ Clear Cart",
        "btn.proceed_checkout": "💳 Proceed to Checkout",
        "btn.remove_item": "❌ Remove {item_name}",
        "btn.use_all_bonus": "Use all {amount} {currency}",
        "btn.apply_bonus_yes": "✅ Yes, apply bonus",
        "btn.apply_bonus_no": "❌ No, save for later",
        "btn.cancel": "❌ Cancel",
        "btn.add_to_cart": "🛒 Add to Cart",

        # === Cart Management ===
        "cart.add_success": "✅ {item_name} added to cart!",
        "cart.add_error": "❌ {message}",
        "cart.empty": "🛒 Your cart is empty.\n\nBrowse the shop to add items!",
        "cart.title": "🛒 <b>Your Shopping Cart</b>\n\n",
        "cart.removed_success": "Item removed from cart",
        "cart.cleared_success": "✅ Cart cleared successfully!",
        "cart.empty_alert": "Cart is empty!",
        "cart.summary_title": "📦 <b>Order Summary</b>\n\n",
        "cart.saved_delivery_info": "Your saved delivery information:\n\n",
        "cart.delivery_address": "📍 Address: {address}\n",
        "cart.delivery_phone": "📞 Phone: {phone}\n",
        "cart.delivery_note": "📝 Note: {note}\n",
        "order.expired.bonus_refund_notification": (
            "⏱️ <b>Order Expired</b>\n\n"
            "Your order <b>{code}</b> has expired due to payment timeout.\n\n"
            "💰 <b>Bonus Refund: {bonus} {currency}</b>\n"
            "📊 New Bonus Balance: <b>{balance} {currency}</b>\n\n"
            "Your referral bonus has been returned to your account.\n"
            "You can use it for your next order!"
        ),
        # === Reference Codes ===
        "refcode.type_admin": "Admin",
        "refcode.type_user": "User",
        "refcode.type_admin_emoji": "👑 Admin",
        "refcode.type_user_emoji": "👤 User",
        "refcode.status_active": "✅ Active",
        "refcode.status_inactive": "❌ Inactive",
        "refcode.never": "Never",
        "refcode.unlimited": "Unlimited",
        "refcode.none_note": "None",
        "refcode.expires_hours": "{hours} hours",
        "refcode.user.prompt_enter": "🔑 Please enter your reference code to access the shop.\n\nIf you don't have a reference code, please contact the administrator.",
        "refcode.user.error_retry": "❌ {error}\n\nPlease try again or contact the administrator.",
        "refcode.user.welcome": "✅ Welcome! Your reference code has been validated.\nYou now have access to the shop.",
        "refcode.user.registration_cancelled": "Registration cancelled. Send /start to try again.",
        "refcode.user.my_none": "You haven't created any reference codes yet.\n\nUsers can create reference codes that are valid for 24 hours and can be used by 1 person.",
        "refcode.user.my_title": "📋 Your Reference Codes:\n\n",
        "refcode.user.my_entry": "🔑 <code>{code}</code>\n   Type: {type}\n   Uses: {current}/{max}\n   Expires: {expires}\n   Status: {status}\n\n",
        "refcode.user.create_existing": "ℹ️ You already have an active reference code:\n\n🔑 Code: <code>{code}</code>\n\n⏰ Expires: {expires}\n👤 Uses: {current}/{max}\n\n💡 You can only have one active code at a time.\nWait for it to expire or be used before creating a new one.",
        "refcode.user.create_success": "✅ Your reference code has been created!\n\n🔑 Code: <code>{code}</code>\n\n⏰ Valid for: 24 hours\n👤 Can be used by: 1 person\n\nShare this code with someone to invite them to the shop!",
        "refcode.user.create_error": "❌ Error creating reference code: {error}",
        "refcode.admin.access_denied": "❌ Access denied",
        "refcode.admin.menu": "🔑 <b>Reference Code Management</b>\n\nManage reference codes for shop access control.\n\nAdmin codes can have custom expiry and usage limits.",
        "refcode.admin.create_prompt_expires": "➕ <b>Create Reference Code</b>\n\nEnter the expiration time in hours:\n• Send <code>0</code> for no expiry\n• Send <code>24</code> for 24 hours\n• Send <code>168</code> for 1 week\n\nOr click Back to cancel.",
        "refcode.admin.hours_positive": "❌ Hours must be positive or 0 (no expiry)",
        "refcode.admin.enter_valid_number": "❌ Please enter a valid number",
        "refcode.admin.create_prompt_max_uses": "👥 <b>Maximum Uses</b>\n\nEnter the maximum number of uses:\n• Send <code>0</code> for unlimited\n• Send <code>1</code> for single use\n• Send <code>10</code> for 10 uses\n\nOr click Back to cancel.",
        "refcode.admin.max_uses_positive": "❌ Max uses must be positive or 0 (unlimited)",
        "refcode.admin.create_prompt_note": "📝 <b>Optional Note</b>\n\nEnter an optional note for this code (e.g., 'VIP customers', 'Marketing campaign'):\n\n• Send note text\n• Or send <code>skip</code> to skip\n\nOr click Back to cancel.",
        "refcode.admin.created": "✅ <b>Reference Code Created!</b>\n\n🔑 Code: <code>{code}</code>\n\n⏰ Expires in: {expires}\n👤 Max uses: {max_uses}\n📝 Note: {note}\n\nShare this code to grant shop access.",
        "refcode.admin.create_error": "❌ Error creating code: {error}",
        "refcode.admin.list_none": "ℹ️ No reference codes found.",
        "refcode.admin.list_title": "📋 <b>Reference Codes</b> (Latest 20)\n\n",
        "refcode.admin.list_entry": "{status} <code>{code}</code> {type}\n   Uses: {current}/{max} | Expires: {expires}\n",
        "refcode.admin.list_note": "   Note: {note}\n",
        "cart.use_info_question": "\n\nWould you like to use this information or update it?",
        "cart.no_saved_info": "❌ No saved delivery information found. Please enter manually.",

        # === Order/Delivery Flow ===
        "order.delivery.address_prompt": "📍 Please enter your delivery address:",
        "order.delivery.address_invalid": "❌ Please provide a valid delivery address (at least 5 characters).",
        "order.delivery.phone_prompt": "📞 Please enter your phone number (with country code):",
        "order.delivery.phone_invalid": "❌ Please provide a valid phone number (at least 8 digits).",
        "order.delivery.note_prompt": "📝 Any special delivery instructions? (Optional)\n\nYou can skip this by clicking the button below.",
        "order.delivery.info_save_error": "❌ Error saving delivery information. Please try again.",

        # === Bonus/Referral Application ===
        "order.bonus.available": "💰 <b>You have {bonus_balance} {currency} in referral bonuses!</b>\n\n",
        "order.bonus.apply_question": "Would you like to apply referral bonus to this order?",
        "order.bonus.amount_positive_error": "❌ Please enter a positive amount.",
        "order.bonus.amount_too_high": "❌ Amount too high. Maximum applicable: {max_applicable} {currency}\nPlease enter a valid amount:",
        "order.bonus.invalid_amount": "❌ Invalid amount. Please enter a number (e.g., 5.50):",
        "order.bonus.insufficient": "❌ Insufficient bonus balance. Please try again.",
        "order.bonus.enter_amount": "Enter the bonus amount you want to apply (maximum {max_applicable} {currency}):\n\nOr use all available bonuses by clicking the button below.",

        # === Payment Instructions ===
        "order.payment.system_unavailable": "❌ <b>Payment System Temporarily Unavailable</b>\n\nNo Bitcoin addresses available. Please contact support.",
        "order.payment.customer_not_found": "❌ Customer info not found. Please try again.",
        "order.payment.creation_error": "❌ Error creating orders. Please try again or contact support.",

        # === Order Summary/Total ===
        "order.summary.title": "📦 <b>Order Summary</b>\n\n",
        "order.summary.cart_total": "Cart Total: {cart_total} {currency}",
        "order.summary.bonus_applied": "Bonus Applied: -{bonus_applied} {currency}",
        "order.summary.final_amount": "Final Amount: {final_amount} {currency}",

        # === Inventory/Reservation ===
        "order.inventory.unable_to_reserve": "❌ <b>Unable to Reserve Items</b>\n\nThe following items are not available in the requested quantities:\n\n{unavailable_items}\n\nPlease adjust your cart and try again.",

        # === My Orders View ===
        "myorders.title": "📦 <b>My Orders</b>\n\n",
        "myorders.total": "Total Orders: {count}",
        "myorders.active": "⏳ Active Orders: {count}",
        "myorders.delivered": "✅ Delivered: {count}",
        "myorders.select_category": "Select a category to view orders:",
        "myorders.active_orders": "⏳ Active Orders",
        "myorders.delivered_orders": "✅ Delivered Orders",
        "myorders.all_orders": "📋 All Orders",
        "myorders.no_orders_yet": "You haven't placed any orders yet.\n\nBrowse the shop to start shopping!",
        "myorders.browse_shop": "🛍️ Go to Shop",
        "myorders.back": "◀️ Back",
        "myorders.all_title": "📋 All Orders",
        "myorders.active_title": "⏳ Active Orders",
        "myorders.delivered_title": "✅ Delivered Orders",
        "myorders.invalid_filter": "Invalid filter",
        "myorders.not_found": "Orders not found.",
        "myorders.back_to_menu": "◀️ Back to Orders Menu",
        "myorders.select_details": "Select an order to view details:",
        "myorders.order_not_found": "Order not found",

        # === Order Details Display ===
        "myorders.detail.title": "📦 <b>Order Details #{order_code}</b>\n\n",
        "myorders.detail.status": "📊 <b>Status:</b> {status}\n",
        "myorders.detail.subtotal": "💵 <b>Subtotal:</b> {subtotal} {currency}\n",
        "myorders.detail.bonus_applied": "🎁 <b>Bonus Applied:</b> {bonus} {currency}\n",
        "myorders.detail.final_price": "💰 <b>Final Price:</b> {total} {currency}\n",
        "myorders.detail.total_price": "💰 <b>Total Price:</b> {total} {currency}\n",
        "myorders.detail.payment_method": "💳 <b>Payment Method:</b> {method}\n",
        "myorders.detail.ordered": "📅 <b>Ordered:</b> {date}\n",
        "myorders.detail.delivery_time": "🚚 <b>Scheduled Delivery:</b> {time}\n",
        "myorders.detail.completed": "✅ <b>Completed:</b> {date}\n",
        "myorders.detail.items": "\n📦 <b>Items:</b>\n{items}\n",
        "myorders.detail.delivery_info": "\n📍 <b>Delivery Information:</b>\n{address}\n{phone}\n{note}",

        # === Help System ===
        "help.prompt": "📧 <b>Need help?</b>\n\n",
        "help.describe_issue": "Please describe your issue or question, and it will be sent directly to the administrator.\n\nType your message below:",
        "help.admin_not_configured": "❌ Sorry, admin contact is not configured. Please try again later.",
        "help.admin_notification_title": "📧 <b>New Help Request</b>\n\n",
        "help.admin_notification_from": "<b>From:</b> @{username} (ID: {user_id})\n",
        "help.admin_notification_message": "<b>Message:</b>\n{message}",
        "help.sent_success": "✅ {auto_message}",
        "help.sent_error": "❌ Failed to send message to admin: {error}\n\nPlease try again later.",
        "help.cancelled": "Help request cancelled.",

        # === Admin Order Notifications ===
        "admin.order.action_required_title": "⏳ <b>Action Required:</b>",
        "admin.order.address_label": "Address: {address}",
        "admin.order.amount_to_collect_label": "<b>Amount to Collect: {amount} {currency}</b>",
        "admin.order.amount_to_receive_label": "<b>Amount to Receive: {amount} {currency}</b>",
        "admin.order.awaiting_payment_status": "⏳ Awaiting payment confirmation...",
        "admin.order.bitcoin_address_label": "Bitcoin Address: <code>{address}</code>",
        "admin.order.bonus_applied_label": "Bonus Applied: <b>-{amount} {currency}</b>",
        "admin.order.customer_label": "Customer: {username} (ID: {id})",
        "admin.order.delivery_info_title": "<b>Delivery Information:</b>",
        "admin.order.items_title": "<b>Items:</b>",
        "admin.order.new_bitcoin_order": "🔔 <b>New BITCOIN Order Received</b>",
        "admin.order.new_cash_order": "🔔 <b>New CASH Order Received</b> 💵",
        "admin.order.note_label": "Note: {note}",
        "admin.order.order_label": "Order: <b>{code}</b>",
        "admin.order.payment_cash": "Cash on Delivery",
        "admin.order.payment_header": "\n<b>Payment:</b>\n",
        "admin.order.payment_method_label": "Payment Method: <b>{method}</b>",
        "admin.order.phone_label": "Phone: {phone}",
        "admin.order.subtotal_label": "Subtotal: <b>{amount} {currency}</b>",
        "admin.order.total_label": "<b>Total: {amount} {currency}</b>\n\n",
        "admin.order.use_cli_confirm": "Use CLI to confirm order and set delivery time:\n<code>python bot_cli.py order --order-code {code} --status-confirmed --delivery-time \"YYYY-MM-DD HH:MM\"</code>",
        "btn.admin.back_to_panel": "🔙 Back to Admin Panel",
        "btn.admin.create_refcode": "➕ Create Reference Code",
        "btn.admin.list_refcodes": "📋 List All Codes",
        "btn.back_to_orders": "◀️ Back to Orders",
        "btn.create_reference_code": "➕ Create Reference Code",
        "btn.my_reference_codes": "🔑 My Reference Codes",
        "btn.need_help": "❓ Need Help?",
        "cart.item.price_format": "  Price: {price} {currency} × {quantity}",
        "cart.item.subtotal_format": "  Subtotal: {subtotal} {currency}",
        "cart.total_format": "<b>Total: {total} {currency}</b>",
        "help.pending_order.contact_support": "Use the /help command to contact support.",
        "help.pending_order.issues_title": "<b>Having issues?</b>",
        "help.pending_order.status": "Your order is currently pending payment.",
        "help.pending_order.step1": "1. Send the exact amount to the Bitcoin address shown",
        "help.pending_order.step2": "2. Wait for blockchain confirmation (usually 10-60 minutes)",
        "help.pending_order.step3": "3. Admin will confirm your payment and schedule a delivery time",
        "help.pending_order.step4": "4. Your goods will be delivered by courier.",
        "help.pending_order.title": "❓ <b>Need Help with Your Order?</b>",
        "help.pending_order.what_to_do_title": "<b>What to do:</b>",
        "myorders.detail.bitcoin_address_label": "Bitcoin Address:",
        "myorders.detail.bitcoin_admin_confirm": "After payment, our admin will confirm your order.",
        "myorders.detail.bitcoin_send_instruction": "⚠️ Please send <b>{amount} {currency}</b> worth of Bitcoin to this address.",
        "myorders.detail.cash_awaiting_confirm": "Your order is awaiting admin confirmation.",
        "myorders.detail.cash_payment_courier": "Payment will be made to the courier upon delivery.",
        "myorders.detail.cash_title": "💵 Cash on Delivery",
        "myorders.detail.cash_will_notify": "You will be notified when your order is confirmed and delivery time is set.",
        "myorders.detail.confirmed_title": "✅ <b>Order Confirmed!</b>",
        "myorders.detail.delivered_thanks_message": "Thank you for your purchase! We hope to see you again! 🙏",
        "myorders.detail.delivered_title": "📦 <b>Order Delivered!</b>",
        "myorders.detail.payment_info_title": "<b>Payment Information:</b>",
        "myorders.detail.preparing_message": "Your order is being prepared for delivery.",
        "myorders.detail.scheduled_delivery_label": "Scheduled delivery: <b>{time}</b>",
        "myorders.order_summary_format": "{status_emoji} {code} - {items_count} items - {total} {currency}",
        "order.bonus.available_label": "Available bonus: <b>{amount} {currency}</b>",
        "order.bonus.choose_amount_hint": "You can choose how much to use (up to {max_amount} {currency})",
        "order.bonus.enter_amount_title": "💵 <b>Enter the bonus amount to apply</b>",
        "order.bonus.max_applicable_label": "Maximum applicable: <b>{amount} {currency}</b>",
        "order.bonus.order_total_label": "Order total: <b>{amount} {currency}</b>",
        "order.info.view_status_hint": "💡 You can view your order status anytime using the /orders command.",
        "order.payment.bitcoin.address_title": "<b>Bitcoin Payment Address:</b>",
        "order.payment.bitcoin.admin_confirm": "• After payment, our admin will confirm your order",
        "order.payment.bitcoin.delivery_title": "<b>Delivery:</b>",
        "order.payment.bitcoin.important_title": "⚠️ <b>IMPORTANT:</b>",
        "order.payment.bitcoin.items_title": "<b>Items:</b>",
        "order.payment.bitcoin.need_help": "Need help? Use /help to contact support.",
        "order.payment.bitcoin.one_time_address": "• This address is for ONE-TIME use only",
        "order.payment.bitcoin.order_code": "Order: <b>{code}</b>",
        "order.payment.bitcoin.send_exact": "• Send the EXACT amount shown above",
        "order.payment.bitcoin.title": "💳 <b>Bitcoin Payment Instructions</b>",
        "order.payment.bitcoin.total_amount": "Total Amount: <b>{amount} {currency}</b>",
        "order.payment.cash.admin_contact": "Admin will contact you shortly.",
        "order.payment.cash.after_confirm": "After confirmation, you will be notified of the delivery time.",
        "order.payment.cash.created": "Your order {code} has been created and is awaiting admin confirmation.",
        "order.payment.cash.important": "⏳ <b>Important:</b> The order is reserved for a limited time.",
        "order.payment.cash.items_title": "Items:",
        "order.payment.cash.payment_to_courier": "Payment will be made to the courier upon delivery.",
        "order.payment.cash.title": "💵 <b>Cash on Delivery</b>",
        "order.payment.cash.total": "Total: {amount}",
        "order.payment.error_general": "❌ Error creating order. Please try again or contact support.",
        "order.summary.total_label": "<b>Total: {amount} {currency}</b>",
        "order.payment.bonus_applied_label": "Bonus Applied: <b>-{amount} {currency}</b>",
        "order.payment.cash.amount_with_bonus": "<b>Amount to Pay on Delivery: {amount} {currency}</b>",
        "order.payment.cash.total_label": "<b>Total to Pay on Delivery: {amount} {currency}</b>",
        "order.payment.final_amount_label": "<b>Final Amount to Pay: {amount} {currency}</b>",
        "order.payment.order_label": "📋 <b>Order: {code}</b>",
        "order.payment.subtotal_label": "Subtotal: <b>{amount} {currency}</b>",
        "order.payment.total_amount_label": "<b>Total Amount: {amount} {currency}</b>",
    },
}
