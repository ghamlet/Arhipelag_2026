import asyncio
import re
from datetime import datetime
from typing import Optional, List, Dict
import pandas as pd
from playwright.async_api import async_playwright, Page

async def login(page: Page, email: str, password: str) -> None:
    """Вход в систему"""
    try:
        await page.wait_for_timeout(3000)
        
        if 'leader-id.ru' in page.url:
            print("🔑 Редирект на Leader-ID...")
            try:
                await page.wait_for_selector('input[type="password"]', timeout=10000)
            except:
                return
        
        password_input = page.locator('input[type="password"]')
        if await password_input.count() > 0:
            print("📝 Ввод учетных данных...")
            
            email_input = page.locator('input[type="text"], input[type="email"]').first
            if await email_input.count() > 0:
                await email_input.fill(email)
            
            await password_input.first.fill(password)
            
            submit_button = page.get_by_role("button", name="Войти")
            if await submit_button.count() == 0:
                submit_button = page.locator('button[type="submit"]').first
            
            if await submit_button.count() > 0:
                await submit_button.click()
                await page.wait_for_timeout(3000)
        else:
            print("ℹ️ Уже в системе")
            
    except Exception as e:
        print(f"ℹ️ Логин: {str(e)[:100]}")

async def main() -> None:
    timetable_url = "https://steps.2035.university/timetable"
    
    async with async_playwright() as p:
        print("🚀 Запуск браузера...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        print("🔑 Переход на страницу...")
        await page.goto(timetable_url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        
        await login(page, "dmtr317744@gmail.com", "14easy2007")
        
        print("\n🛑 ПАУЗА ДЛЯ ЧЕЛОВЕКА!")
        print("Разгадайте капчу и дождитесь загрузки расписания.")
        input("👉 Нажмите [ENTER] когда готово...")
        
        # Закрываем куки
        try:
            await page.get_by_role("button", name="Согласен").click(timeout=2000)
        except:
            pass
        
        # Ждем карточки
        selector_titles = '[id^="event-"] div.event__content-wrap h3'
        
        for attempt in range(3):
            try:
                await page.wait_for_selector(selector_titles, timeout=15000)
                break
            except:
                print(f"⚠️ Попытка {attempt + 1}: ждем карточки...")
                await page.wait_for_timeout(5000)
                if attempt == 2:
                    await page.reload(timeout=30000, wait_until='domcontentloaded')
                    await page.wait_for_timeout(5000)
        
        cards_count = await page.locator(selector_titles).count()
        print(f"📊 Найдено карточек: {cards_count}")
        
        if cards_count == 0:
            print("❌ Карточки не найдены")
            await browser.close()
            return
        
        # Собираем данные
        unique_events = {}
        content_selector = "#__nuxt > div > div.h-100.d-flex.flex-column.default-layout > div.overlay__wrap.xle > div > div.overlay__wrap.container > div"
        
        for i in range(cards_count):
            print(f"\n🔄 Карточка {i+1}/{cards_count}")
            
            try:
                current_card = page.locator(selector_titles).nth(i)
                await current_card.scroll_into_view_if_needed()
                card_text = await current_card.inner_text()
                print(f"📌 {card_text.strip()}")
                
                # Кликаем
                try:
                    await current_card.click(timeout=5000)
                except:
                    await current_card.evaluate('el => el.click()')
                
                await page.wait_for_timeout(5000)
                
                # Берем ВЕСЬ текст из контента
                try:
                    content_element = page.locator(content_selector)
                    if await content_element.count() > 0:
                        full_text = await content_element.inner_text()
                    else:
                        full_text = await page.locator("body").inner_text()
                except:
                    full_text = await page.locator("body").inner_text()
                
                # Извлекаем название из h1
                clean_name = ""
                try:
                    h1 = page.locator("section.page-title_event h1")
                    if await h1.count() > 0:
                        h1_text = await h1.inner_text()
                        clean_name = re.sub(r'\.?\s*День\s+\d+', '', h1_text).strip()
                except:
                    pass
                
                # Если не нашли через h1, используем текст карточки
                if not clean_name:
                    clean_name = re.sub(r'\.?\s*День\s+\d+', '', card_text).strip()
                
                if not clean_name:
                    clean_name = f"Событие_{i+1}"
                
                # Сохраняем только уникальные названия
                if clean_name not in unique_events:
                    unique_events[clean_name] = {
                        'name': clean_name,
                        'full_text': full_text,
                        'url': page.url
                    }
                    print(f"✅ Сохранено: {clean_name}")
                else:
                    print(f"⏭️ Уже есть: {clean_name}")
                
            except Exception as e:
                print(f"❌ Ошибка: {str(e)[:200]}")
            
            # Возвращаемся
            print("⬅️ Назад...")
            try:
                await page.goto(timetable_url, timeout=30000, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                await page.wait_for_selector(selector_titles, timeout=10000)
            except:
                await page.wait_for_timeout(5000)
        
        await browser.close()
    
    # Выводим результаты
    print("\n" + "="*80)
    print(f"СОБРАНО УНИКАЛЬНЫХ СОРЕВНОВАНИЙ: {len(unique_events)}")
    print("="*80)
    
    events_list = list(unique_events.values())
    
    for i, event in enumerate(events_list, 1):
        print(f"\n{i}. {event['name']}")
        print(f"   URL: {event['url']}")
        print(f"   Текст: {event['full_text'][:200]}...")
    
    # Сохраняем в файлы
    if events_list:
        # CSV
        df = pd.DataFrame(events_list)
        df.to_csv('events_full_text.csv', index=False, encoding='utf-8-sig')
        print(f"\n💾 CSV сохранен: events_full_text.csv")
        
        # Текстовый файл со всеми текстами
        with open('events_texts.txt', 'w', encoding='utf-8') as f:
            for event in events_list:
                f.write(f"{'='*80}\n")
                f.write(f"НАЗВАНИЕ: {event['name']}\n")
                f.write(f"URL: {event['url']}\n")
                f.write(f"{'='*80}\n")
                f.write(event['full_text'])
                f.write(f"\n\n")
        print(f"💾 Тексты сохранены: events_texts.txt")

if __name__ == "__main__":
    asyncio.run(main())