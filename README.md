Запуск з кореня проєкту:

    python3 app.py

    python3 features.py

    pip install nbconvert     # один раз
    jupyter nbconvert --to notebook --execute --inplace eda.ipynb   # перераховує весь ноутбук

    python3 models.py

Демо входу (після `python3 app.py`):

    http://localhost:5000/            - одразу відкриває реєстрацію
    http://localhost:5000/register   - створити профіль: набрати пароль SS123+ 15 разів
    http://localhost:5000/login      - увійти: перевіряється пароль і ритм набору

Профілі зберігаються в `data/users.json` і `data/profiles/` (у git вони не потрапляють).
Кількість спроб для реєстрації можна змінити: `ENROLL_ATTEMPTS=20 python3 app.py`.

Сторінка збору даних тепер тут: http://localhost:5000/collector
