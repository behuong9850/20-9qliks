import streamlit as st
st.image("malibu1234.jpg")
import mysql.connector
from mysql.connector import Error
from datetime import date, datetime
from decimal import Decimal
import pandas as pd

# ============================================================
# CẤU HÌNH STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Hotel Manager",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# MYSQL AIVEN CONFIG
# ============================================================

DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_TX2oBXmTGGjXba6p7j1"
DB_HOST = "mysql-3a5ef2bc-binhquytoc.a.aivencloud.com"
DB_PORT = 14483
DB_NAME = "hotel_mangement"

# Nếu Aiven yêu cầu SSL, để True.
DB_SSL = True


# ============================================================
# KẾT NỐI MYSQL
# ============================================================

def get_connection():
    """
    Tạo kết nối đến MySQL Aiven.
    """

    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
        "connection_timeout": 15,
        "autocommit": False,
    }

    if DB_SSL:
        config["ssl_verify_cert"] = False
        config["ssl_verify_identity"] = False

    return mysql.connector.connect(**config)


# ============================================================
# KHỞI TẠO DATABASE
# ============================================================

def init_database():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ----------------------------------------------------
        # ROOMS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_number VARCHAR(20) NOT NULL UNIQUE,
                room_type VARCHAR(50) NOT NULL,
                floor INT NOT NULL,
                price DECIMAL(15,2) NOT NULL DEFAULT 0,
                status VARCHAR(30) NOT NULL DEFAULT 'Trống',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)

        # ----------------------------------------------------
        # GUESTS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(150) NOT NULL,
                phone VARCHAR(30),
                email VARCHAR(150),
                id_number VARCHAR(50),
                address VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                INDEX idx_guest_name (full_name),
                INDEX idx_guest_phone (phone),
                INDEX idx_guest_id_number (id_number)
            ) ENGINE=InnoDB;
        """)

        # ----------------------------------------------------
        # BOOKINGS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,

                guest_id INT NOT NULL,
                room_id INT NOT NULL,

                check_in DATE NOT NULL,
                check_out DATE NOT NULL,

                adults INT NOT NULL DEFAULT 1,
                children INT NOT NULL DEFAULT 0,

                status VARCHAR(30) NOT NULL DEFAULT 'Đã đặt',

                total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                paid_amount DECIMAL(15,2) NOT NULL DEFAULT 0,

                note TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,

                CONSTRAINT fk_booking_guest
                    FOREIGN KEY (guest_id)
                    REFERENCES guests(id),

                CONSTRAINT fk_booking_room
                    FOREIGN KEY (room_id)
                    REFERENCES rooms(id),

                INDEX idx_booking_room (room_id),
                INDEX idx_booking_guest (guest_id),
                INDEX idx_booking_dates (check_in, check_out),
                INDEX idx_booking_status (status)
            ) ENGINE=InnoDB;
        """)

        # ----------------------------------------------------
        # PAYMENTS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INT AUTO_INCREMENT PRIMARY KEY,

                booking_id INT NOT NULL,

                amount DECIMAL(15,2) NOT NULL,

                payment_method VARCHAR(50)
                    NOT NULL DEFAULT 'Tiền mặt',

                payment_date DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                note TEXT,

                CONSTRAINT fk_payment_booking
                    FOREIGN KEY (booking_id)
                    REFERENCES bookings(id)
                    ON DELETE CASCADE,

                INDEX idx_payment_booking (booking_id)
            ) ENGINE=InnoDB;
        """)

        # ----------------------------------------------------
        # SAMPLE ROOMS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM rooms
        """)

        count = cursor.fetchone()[0]

        if count == 0:

            sample_rooms = [
                ("101", "Deluxe", 1, 1800000),
                ("102", "Deluxe", 1, 1800000),
                ("103", "Deluxe", 1, 1800000),
                ("104", "Superior", 1, 1500000),

                ("201", "Deluxe", 2, 2000000),
                ("202", "Deluxe", 2, 2000000),
                ("203", "Suite", 2, 3500000),
                ("204", "Suite", 2, 3500000),

                ("301", "Deluxe", 3, 2200000),
                ("302", "Deluxe", 3, 2200000),
                ("303", "Suite", 3, 4000000),
                ("304", "VIP", 3, 5500000),
            ]

            cursor.executemany("""
                INSERT INTO rooms
                (
                    room_number,
                    room_type,
                    floor,
                    price,
                    status
                )
                VALUES (%s, %s, %s, %s, 'Trống')
            """, sample_rooms)

        conn.commit()

        return True, "Database MySQL đã sẵn sàng."

    except Error as e:

        if conn:
            conn.rollback()

        return False, f"Lỗi MySQL: {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# HELPER DATABASE
# ============================================================

def execute_query(query, params=None, fetch=False, many=False):

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if many:
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params or ())

        if fetch:

            result = cursor.fetchall()

            conn.close()

            return result

        conn.commit()

        last_id = cursor.lastrowid

        conn.close()

        return last_id

    except Error as e:

        if conn:
            conn.rollback()

        raise e

    finally:

        try:
            if cursor:
                cursor.close()
        except:
            pass

        try:
            if conn:
                conn.close()
        except:
            pass


# ============================================================
# ROOMS
# ============================================================

def fetch_rooms():

    query = """
        SELECT
            id,
            room_number,
            room_type,
            floor,
            price,
            status,
            created_at
        FROM rooms
        ORDER BY floor, room_number
    """

    data = execute_query(query, fetch=True)

    return pd.DataFrame(data)


def add_room(
    room_number,
    room_type,
    floor,
    price
):

    query = """
        INSERT INTO rooms
        (
            room_number,
            room_type,
            floor,
            price,
            status
        )
        VALUES (%s, %s, %s, %s, 'Trống')
    """

    try:

        execute_query(
            query,
            (
                room_number,
                room_type,
                floor,
                price
            )
        )

        return True, "Thêm phòng thành công."

    except Error as e:

        if e.errno == 1062:
            return False, "Số phòng đã tồn tại."

        return False, f"Lỗi: {e}"


def update_room(
    room_id,
    room_number,
    room_type,
    floor,
    price,
    status
):

    query = """
        UPDATE rooms
        SET
            room_number = %s,
            room_type = %s,
            floor = %s,
            price = %s,
            status = %s
        WHERE id = %s
    """

    try:

        execute_query(
            query,
            (
                room_number,
                room_type,
                floor,
                price,
                status,
                room_id
            )
        )

        return True, "Cập nhật phòng thành công."

    except Error as e:

        if e.errno == 1062:
            return False, "Số phòng đã tồn tại."

        return False, f"Lỗi: {e}"


def delete_room(room_id):

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM bookings
            WHERE room_id = %s
        """, (room_id,))

        count = cursor.fetchone()[0]

        if count > 0:

            return (
                False,
                "Không thể xóa phòng vì phòng đã có lịch sử đặt."
            )

        cursor.execute("""
            DELETE FROM rooms
            WHERE id = %s
        """, (room_id,))

        conn.commit()

        return True, "Đã xóa phòng."

    except Error as e:

        if conn:
            conn.rollback()

        return False, str(e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# BOOKINGS
# ============================================================

def fetch_bookings():

    query = """
        SELECT
            b.id,

            g.id AS guest_id,
            g.full_name,
            g.phone,
            g.email,
            g.id_number,

            r.id AS room_id,
            r.room_number,
            r.room_type,

            b.check_in,
            b.check_out,

            b.adults,
            b.children,

            b.status,

            b.total_amount,
            b.paid_amount,

            (b.total_amount - b.paid_amount)
                AS remaining_amount,

            b.note,

            b.created_at

        FROM bookings b

        INNER JOIN guests g
            ON b.guest_id = g.id

        INNER JOIN rooms r
            ON b.room_id = r.id

        ORDER BY b.id DESC
    """

    data = execute_query(
        query,
        fetch=True
    )

    return pd.DataFrame(data)


def get_booking_payments(booking_id):

    query = """
        SELECT
            id,
            booking_id,
            amount,
            payment_method,
            payment_date,
            note
        FROM payments
        WHERE booking_id = %s
        ORDER BY payment_date DESC
    """

    return pd.DataFrame(
        execute_query(
            query,
            (booking_id,),
            fetch=True
        )
    )


# ============================================================
# KIỂM TRA PHÒNG TRÙNG LỊCH
# ============================================================

def check_room_available(
    room_id,
    check_in,
    check_out
):

    query = """
        SELECT COUNT(*)
        FROM bookings
        WHERE room_id = %s

        AND status NOT IN ('Hủy', 'Đã trả phòng')

        AND check_in < %s
        AND check_out > %s
    """

    result = execute_query(
        query,
        (
            room_id,
            check_out,
            check_in
        ),
        fetch=True
    )

    return result[0]["COUNT(*)"] == 0


# ============================================================
# CREATE BOOKING
# ============================================================

def create_booking(
    full_name,
    phone,
    email,
    id_number,
    address,
    room_id,
    check_in,
    check_out,
    adults,
    children,
    note
):

    conn = None
    cursor = None

    try:

        if check_out <= check_in:

            raise ValueError(
                "Ngày trả phòng phải sau ngày nhận phòng."
            )

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # ----------------------------------------------------
        # CHECK ROOM
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                price,
                status
            FROM rooms
            WHERE id = %s
            FOR UPDATE
        """, (room_id,))

        room = cursor.fetchone()

        if not room:
            raise ValueError(
                "Không tìm thấy phòng."
            )

        # ----------------------------------------------------
        # CHECK OVERLAPPING BOOKINGS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE room_id = %s

            AND status NOT IN ('Hủy', 'Đã trả phòng')

            AND check_in < %s
            AND check_out > %s
        """, (
            room_id,
            check_out,
            check_in
        ))

        conflict = cursor.fetchone()["total"]

        if conflict > 0:

            raise ValueError(
                "Phòng đã có booking trong khoảng thời gian này."
            )

        # ----------------------------------------------------
        # GUEST
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO guests
            (
                full_name,
                phone,
                email,
                id_number,
                address
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            full_name,
            phone,
            email,
            id_number,
            address
        ))

        guest_id = cursor.lastrowid

        # ----------------------------------------------------
        # CALCULATE TOTAL
        # ----------------------------------------------------

        nights = (
            check_out - check_in
        ).days

        total = Decimal(
            str(room["price"])
        ) * nights

        # ----------------------------------------------------
        # BOOKING
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO bookings
            (
                guest_id,
                room_id,
                check_in,
                check_out,
                adults,
                children,
                status,
                total_amount,
                paid_amount,
                note
            )
            VALUES
            (
                %s, %s, %s, %s,
                %s, %s, 'Đã đặt',
                %s, 0, %s
            )
        """, (
            guest_id,
            room_id,
            check_in,
            check_out,
            adults,
            children,
            total,
            note
        ))

        # ----------------------------------------------------
        # ROOM STATUS
        # ----------------------------------------------------

        # Chỉ cập nhật trạng thái vật lý khi booking bắt đầu
        # hoặc trong giao diện nhân viên cập nhật trạng thái.

        conn.commit()

        return (
            True,
            f"Đặt phòng thành công. "
            f"{nights} đêm - "
            f"Tổng tiền: {format_money(total)}"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        return False, str(e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# UPDATE BOOKING STATUS
# ============================================================

def update_booking_status(
    booking_id,
    new_status
):

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT room_id
            FROM bookings
            WHERE id = %s
        """, (booking_id,))

        booking = cursor.fetchone()

        if not booking:

            return False, "Không tìm thấy booking."

        room_id = booking["room_id"]

        cursor.execute("""
            UPDATE bookings
            SET status = %s
            WHERE id = %s
        """, (
            new_status,
            booking_id
        ))

        room_status = {
            "Đã đặt": "Đã đặt",
            "Đang ở": "Đang ở",
            "Đã trả phòng": "Đang dọn",
            "Hủy": "Trống"
        }.get(
            new_status,
            "Trống"
        )

        cursor.execute("""
            UPDATE rooms
            SET status = %s
            WHERE id = %s
        """, (
            room_status,
            room_id
        ))

        conn.commit()

        return True, "Đã cập nhật trạng thái."

    except Error as e:

        if conn:
            conn.rollback()

        return False, str(e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# PAYMENT
# ============================================================

def make_payment(
    booking_id,
    amount,
    method,
    note
):

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # ----------------------------------------------------
        # LOCK BOOKING
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                total_amount,
                paid_amount
            FROM bookings
            WHERE id = %s
            FOR UPDATE
        """, (booking_id,))

        booking = cursor.fetchone()

        if not booking:

            return False, "Không tìm thấy booking."

        total = Decimal(
            str(booking["total_amount"])
        )

        paid = Decimal(
            str(booking["paid_amount"])
        )

        amount = Decimal(
            str(amount)
        )

        if amount <= 0:

            return False, (
                "Số tiền thanh toán phải lớn hơn 0."
            )

        if paid + amount > total:

            return False, (
                "Số tiền thanh toán vượt quá "
                "tổng tiền booking."
            )

        # ----------------------------------------------------
        # INSERT PAYMENT
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO payments
            (
                booking_id,
                amount,
                payment_method,
                note
            )
            VALUES (%s, %s, %s, %s)
        """, (
            booking_id,
            amount,
            method,
            note
        ))

        # ----------------------------------------------------
        # UPDATE PAID
        # ----------------------------------------------------

        new_paid = paid + amount

        cursor.execute("""
            UPDATE bookings
            SET paid_amount = %s
            WHERE id = %s
        """, (
            new_paid,
            booking_id
        ))

        conn.commit()

        return (
            True,
            f"Đã ghi nhận thanh toán "
            f"{format_money(amount)}."
        )

    except Error as e:

        if conn:
            conn.rollback()

        return False, str(e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# FORMAT
# ============================================================

def format_money(value):

    if value is None:
        value = 0

    try:
        return f"{float(value):,.0f} VNĐ"

    except:
        return "0 VNĐ"


def status_icon(status):

    mapping = {
        "Trống": "🟢",
        "Đã đặt": "🟡",
        "Đang ở": "🔵",
        "Đang dọn": "🟠",
        "Bảo trì": "🔴"
    }

    return mapping.get(
        status,
        "⚪"
    )


# ============================================================
# DATABASE STATUS
# ============================================================

db_ok, db_message = init_database()

if not db_ok:

    st.error(
        "❌ Không thể kết nối MySQL Aiven"
    )

    st.code(
        db_message
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🏨 HOTEL MANAGER"
)

st.sidebar.caption(
    "MySQL Aiven Edition"
)

menu = st.sidebar.radio(
    "MENU",
    [
        "📊 Tổng quan",
        "🛏️ Quản lý phòng",
        "📅 Đặt phòng",
        "👤 Khách lưu trú",
        "💳 Thanh toán",
        "📈 Báo cáo doanh thu"
    ]
)

st.sidebar.divider()

st.sidebar.success(
    "🟢 MySQL Aiven: Connected"
)


# ============================================================
# TỔNG QUAN
# ============================================================

if menu == "📊 Tổng quan":

    st.title(
        "📊 Tổng quan khách sạn"
    )

    st.caption(
        f"Cập nhật: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

    rooms = fetch_rooms()
    bookings = fetch_bookings()

    total_rooms = len(rooms)

    def count_status(status):

        if rooms.empty:
            return 0

        return len(
            rooms[
                rooms["status"] == status
            ]
        )

    empty_rooms = count_status("Trống")
    reserved_rooms = count_status("Đã đặt")
    occupied_rooms = count_status("Đang ở")
    cleaning_rooms = count_status("Đang dọn")
    maintenance_rooms = count_status("Bảo trì")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(
        "Tổng phòng",
        total_rooms
    )

    col2.metric(
        "🟢 Trống",
        empty_rooms
    )

    col3.metric(
        "🟡 Đã đặt",
        reserved_rooms
    )

    col4.metric(
        "🔵 Đang ở",
        occupied_rooms
    )

    col5.metric(
        "🟠 Đang dọn",
        cleaning_rooms
    )

    col6.metric(
        "🔴 Bảo trì",
        maintenance_rooms
    )

    st.divider()

    # --------------------------------------------------------
    # OCCUPANCY
    # --------------------------------------------------------

    if total_rooms > 0:

        occupied = (
            reserved_rooms
            + occupied_rooms
        )

        occupancy = (
            occupied / total_rooms
        ) * 100

        st.subheader(
            "📊 Công suất phòng"
        )

        st.progress(
            min(occupancy / 100, 1.0)
        )

        st.write(
            f"Công suất hiện tại: "
            f"**{occupancy:.1f}%**"
        )

    st.divider()

    # --------------------------------------------------------
    # ROOM MAP
    # --------------------------------------------------------

    st.subheader(
        "🏨 Sơ đồ phòng"
    )

    if rooms.empty:

        st.info(
            "Chưa có phòng."
        )

    else:

        floors = sorted(
            rooms["floor"].unique()
        )

        for floor in floors:

            st.markdown(
                f"### Tầng {floor}"
            )

            floor_rooms = rooms[
                rooms["floor"] == floor
            ]

            columns = st.columns(4)

            for index, (_, room) in enumerate(
                floor_rooms.iterrows()
            ):

                with columns[
                    index % 4
                ]:

                    st.markdown(
                        f"""
                        <div style="
                            border:1px solid #ddd;
                            border-radius:12px;
                            padding:16px;
                            margin-bottom:12px;
                            background:#fafafa;
                        ">
                            <h3>
                                🚪 {room['room_number']}
                            </h3>

                            <p>
                                <b>
                                    {room['room_type']}
                                </b>
                            </p>

                            <p>
                                {status_icon(room['status'])}
                                {room['status']}
                            </p>

                            <p>
                                💰
                                {format_money(room['price'])}
                                /đêm
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    st.divider()

    st.subheader(
        "📅 Booking gần đây"
    )

    if bookings.empty:

        st.info(
            "Chưa có booking."
        )

    else:

        display = bookings.head(10).copy()

        st.dataframe(
            display[
                [
                    "id",
                    "full_name",
                    "room_number",
                    "check_in",
                    "check_out",
                    "status",
                    "total_amount",
                    "paid_amount",
                    "remaining_amount"
                ]
            ],
            column_config={
                "id": "Booking",
                "full_name": "Khách",
                "room_number": "Phòng",
                "check_in": "Nhận",
                "check_out": "Trả",
                "status": "Trạng thái",
                "total_amount":
                    st.column_config.NumberColumn(
                        "Tổng tiền",
                        format="%,.0f VNĐ"
                    ),
                "paid_amount":
                    st.column_config.NumberColumn(
                        "Đã trả",
                        format="%,.0f VNĐ"
                    ),
                "remaining_amount":
                    st.column_config.NumberColumn(
                        "Còn lại",
                        format="%,.0f VNĐ"
                    )
            },
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# QUẢN LÝ PHÒNG
# ============================================================

elif menu == "🛏️ Quản lý phòng":

    st.title(
        "🛏️ Quản lý phòng"
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Danh sách",
            "➕ Thêm phòng",
            "✏️ Chỉnh sửa"
        ]
    )

    rooms = fetch_rooms()

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    with tab1:

        col1, col2 = st.columns(2)

        with col1:

            search = st.text_input(
                "🔎 Tìm số phòng"
            )

        with col2:

            status_filter = st.selectbox(
                "Lọc trạng thái",
                [
                    "Tất cả",
                    "Trống",
                    "Đã đặt",
                    "Đang ở",
                    "Đang dọn",
                    "Bảo trì"
                ]
            )

        filtered = rooms.copy()

        if search:

            filtered = filtered[
                filtered["room_number"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

        if status_filter != "Tất cả":

            filtered = filtered[
                filtered["status"]
                == status_filter
            ]

        st.dataframe(
            filtered[
                [
                    "id",
                    "room_number",
                    "room_type",
                    "floor",
                    "price",
                    "status"
                ]
            ],
            column_config={
                "id": "ID",
                "room_number": "Số phòng",
                "room_type": "Loại",
                "floor": "Tầng",
                "price":
                    st.column_config.NumberColumn(
                        "Giá/đêm",
                        format="%,.0f VNĐ"
                    ),
                "status": "Trạng thái"
            },
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    with tab2:

        st.subheader(
            "➕ Thêm phòng"
        )

        with st.form(
            "add_room_form"
        ):

            col1, col2 = st.columns(2)

            with col1:

                room_number = st.text_input(
                    "Số phòng *"
                )

                room_type = st.selectbox(
                    "Loại phòng",
                    [
                        "Standard",
                        "Superior",
                        "Deluxe",
                        "Suite",
                        "VIP"
                    ]
                )

            with col2:

                floor = st.number_input(
                    "Tầng",
                    min_value=1,
                    max_value=100,
                    value=1
                )

                price = st.number_input(
                    "Giá phòng/đêm",
                    min_value=0.0,
                    value=1500000.0,
                    step=100000.0
                )

            submit = st.form_submit_button(
                "➕ Thêm phòng",
                use_container_width=True
            )

            if submit:

                if not room_number.strip():

                    st.error(
                        "Vui lòng nhập số phòng."
                    )

                else:

                    success, message = add_room(
                        room_number.strip(),
                        room_type,
                        floor,
                        price
                    )

                    if success:

                        st.success(
                            message
                        )

                        st.rerun()

                    else:

                        st.error(
                            message
                        )

    # --------------------------------------------------------
    # EDIT
    # --------------------------------------------------------

    with tab3:

        if rooms.empty:

            st.info(
                "Chưa có phòng."
            )

        else:

            room_options = {
                f"{row['room_number']} - "
                f"{row['room_type']}":
                    row["id"]
                for _, row in rooms.iterrows()
            }

            selected_room = st.selectbox(
                "Chọn phòng",
                list(
                    room_options.keys()
                )
            )

            selected_id = room_options[
                selected_room
            ]

            room = rooms[
                rooms["id"]
                == selected_id
            ].iloc[0]

            with st.form(
                "edit_room_form"
            ):

                col1, col2 = st.columns(2)

                with col1:

                    edit_number = st.text_input(
                        "Số phòng",
                        value=room[
                            "room_number"
                        ]
                    )

                    types = [
                        "Standard",
                        "Superior",
                        "Deluxe",
                        "Suite",
                        "VIP"
                    ]

                    edit_type = st.selectbox(
                        "Loại phòng",
                        types,
                        index=types.index(
                            room["room_type"]
                        )
                    )

                    edit_floor = st.number_input(
                        "Tầng",
                        min_value=1,
                        max_value=100,
                        value=int(
                            room["floor"]
                        )
                    )

                with col2:

                    edit_price = st.number_input(
                        "Giá phòng",
                        min_value=0.0,
                        value=float(
                            room["price"]
                        ),
                        step=100000.0
                    )

                    statuses = [
                        "Trống",
                        "Đã đặt",
                        "Đang ở",
                        "Đang dọn",
                        "Bảo trì"
                    ]

                    edit_status = st.selectbox(
                        "Trạng thái",
                        statuses,
                        index=statuses.index(
                            room["status"]
                        )
                    )

                col_save, col_delete = st.columns(2)

                with col_save:

                    save = st.form_submit_button(
                        "💾 Lưu",
                        use_container_width=True
                    )

                with col_delete:

                    delete = st.form_submit_button(
                        "🗑️ Xóa",
                        use_container_width=True
                    )

                if save:

                    success, message = update_room(
                        selected_id,
                        edit_number.strip(),
                        edit_type,
                        edit_floor,
                        edit_price,
                        edit_status
                    )

                    if success:

                        st.success(
                            message
                        )

                        st.rerun()

                    else:

                        st.error(
                            message
                        )

                if delete:

                    success, message = delete_room(
                        selected_id
                    )

                    if success:

                        st.success(
                            message
                        )

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


# ============================================================
# ĐẶT PHÒNG
# ============================================================

elif menu == "📅 Đặt phòng":

    st.title(
        "📅 Đặt phòng"
    )

    rooms = fetch_rooms()

    available_rooms = rooms[
        rooms["status"].isin(
            ["Trống", "Đã đặt"]
        )
    ]

    if available_rooms.empty:

        st.warning(
            "Không có phòng để đặt."
        )

    else:

        with st.form(
            "booking_form"
        ):

            st.subheader(
                "👤 Thông tin khách"
            )

            col1, col2 = st.columns(2)

            with col1:

                full_name = st.text_input(
                    "Họ và tên *"
                )

                phone = st.text_input(
                    "Số điện thoại"
                )

                email = st.text_input(
                    "Email"
                )

                id_number = st.text_input(
                    "CCCD / Passport"
                )

                address = st.text_input(
                    "Địa chỉ"
                )

            with col2:

                room_options = {
                    f"Phòng {row['room_number']} - "
                    f"{row['room_type']} - "
                    f"{format_money(row['price'])}/đêm":
                        row["id"]
                    for _, row
                    in available_rooms.iterrows()
                }

                selected_room = st.selectbox(
                    "Chọn phòng *",
                    list(
                        room_options.keys()
                    )
                )

                room_id = room_options[
                    selected_room
                ]

                check_in = st.date_input(
                    "Ngày nhận",
                    value=date.today()
                )

                check_out = st.date_input(
                    "Ngày trả",
                    value=date.today()
                )

                adults = st.number_input(
                    "Người lớn",
                    min_value=1,
                    max_value=20,
                    value=1
                )

                children = st.number_input(
                    "Trẻ em",
                    min_value=0,
                    max_value=20,
                    value=0
                )

            note = st.text_area(
                "Ghi chú"
            )

            submit = st.form_submit_button(
                "📅 Xác nhận đặt phòng",
                use_container_width=True
            )

            if submit:

                if not full_name.strip():

                    st.error(
                        "Vui lòng nhập họ tên."
                    )

                elif check_out <= check_in:

                    st.error(
                        "Ngày trả phải sau ngày nhận."
                    )

                else:

                    success, message = create_booking(
                        full_name.strip(),
                        phone.strip(),
                        email.strip(),
                        id_number.strip(),
                        address.strip(),
                        room_id,
                        check_in,
                        check_out,
                        adults,
                        children,
                        note.strip()
                    )

                    if success:

                        st.success(
                            message
                        )

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


# ============================================================
# KHÁCH LƯU TRÚ
# ============================================================

elif menu == "👤 Khách lưu trú":

    st.title(
        "👤 Khách lưu trú"
    )

    bookings = fetch_bookings()

    if bookings.empty:

        st.info(
            "Chưa có booking."
        )

    else:

        search = st.text_input(
            "🔎 Tìm khách",
            placeholder="Tên hoặc số điện thoại"
        )

        filtered = bookings.copy()

        if search:

            mask = (
                filtered["full_name"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
                |
                filtered["phone"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            )

            filtered = filtered[mask]

        st.dataframe(
            filtered[
                [
                    "id",
                    "full_name",
                    "phone",
                    "email",
                    "id_number",
                    "room_number",
                    "check_in",
                    "check_out",
                    "adults",
                    "children",
                    "status",
                    "total_amount",
                    "paid_amount",
                    "remaining_amount"
                ]
            ],
            column_config={
                "id": "Booking",
                "full_name": "Khách",
                "phone": "Điện thoại",
                "email": "Email",
                "id_number": "CCCD",
                "room_number": "Phòng",
                "check_in": "Nhận",
                "check_out": "Trả",
                "adults": "NL",
                "children": "TE",
                "status": "Trạng thái",
                "total_amount":
                    st.column_config.NumberColumn(
                        "Tổng",
                        format="%,.0f VNĐ"
                    ),
                "paid_amount":
                    st.column_config.NumberColumn(
                        "Đã trả",
                        format="%,.0f VNĐ"
                    ),
                "remaining_amount":
                    st.column_config.NumberColumn(
                        "Còn lại",
                        format="%,.0f VNĐ"
                    )
            },
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.subheader(
            "🔄 Cập nhật trạng thái booking"
        )

        booking_options = {
            f"#{row['id']} - "
            f"{row['full_name']} - "
            f"Phòng {row['room_number']}":
                row["id"]
            for _, row in bookings.iterrows()
        }

        selected = st.selectbox(
            "Chọn booking",
            list(
                booking_options.keys()
            )
        )

        booking_id = booking_options[
            selected
        ]

        new_status = st.selectbox(
            "Trạng thái",
            [
                "Đã đặt",
                "Đang ở",
                "Đã trả phòng",
                "Hủy"
            ]
        )

        if st.button(
            "💾 Cập nhật trạng thái",
            use_container_width=True
        ):

            success, message = update_booking_status(
                booking_id,
                new_status
            )

            if success:

                st.success(
                    message
                )

                st.rerun()

            else:

                st.error(
                    message
                )


# ============================================================
# THANH TOÁN
# ============================================================

elif menu == "💳 Thanh toán":

    st.title(
        "💳 Thanh toán"
    )

    bookings = fetch_bookings()

    if bookings.empty:

        st.info(
            "Chưa có booking."
        )

    else:

        booking_options = {
            f"#{row['id']} - "
            f"{row['full_name']} - "
            f"Phòng {row['room_number']}":
                row["id"]
            for _, row in bookings.iterrows()
        }

        selected = st.selectbox(
            "Chọn booking",
            list(
                booking_options.keys()
            )
        )

        booking_id = booking_options[
            selected
        ]

        booking = bookings[
            bookings["id"] == booking_id
        ].iloc[0]

        total = float(
            booking["total_amount"]
        )

        paid = float(
            booking["paid_amount"]
        )

        remaining = (
            total - paid
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Khách",
            booking["full_name"]
        )

        col2.metric(
            "Tổng tiền",
            format_money(total)
        )

        col3.metric(
            "Đã thanh toán",
            format_money(paid)
        )

        col4.metric(
            "Còn lại",
            format_money(remaining)
        )

        st.divider()

        if remaining <= 0:

            st.success(
                "✅ Booking đã thanh toán đủ."
            )

        else:

            with st.form(
                "payment_form"
            ):

                amount = st.number_input(
                    "Số tiền thanh toán",
                    min_value=0.0,
                    max_value=remaining,
                    value=remaining,
                    step=100000.0
                )

                method = st.selectbox(
                    "Phương thức",
                    [
                        "Tiền mặt",
                        "Chuyển khoản",
                        "Thẻ tín dụng",
                        "Ví điện tử"
                    ]
                )

                note = st.text_area(
                    "Ghi chú"
                )

                submit = st.form_submit_button(
                    "💰 Xác nhận thanh toán",
                    use_container_width=True
                )

                if submit:

                    success, message = make_payment(
                        booking_id,
                        amount,
                        method,
                        note
                    )

                    if success:

                        st.success(
                            message
                        )

                        st.rerun()

                    else:

                        st.error(
                            message
                        )

        st.divider()

        st.subheader(
            "🧾 Lịch sử thanh toán"
        )

        payments = get_booking_payments(
            booking_id
        )

        if payments.empty:

            st.info(
                "Chưa có giao dịch."
            )

        else:

            st.dataframe(
                payments,
                column_config={
                    "id": "ID",
                    "booking_id": "Booking",
                    "amount":
                        st.column_config.NumberColumn(
                            "Số tiền",
                            format="%,.0f VNĐ"
                        ),
                    "payment_method":
                        "Phương thức",
                    "payment_date":
                        "Ngày thanh toán",
                    "note":
                        "Ghi chú"
                },
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# BÁO CÁO DOANH THU
# ============================================================

elif menu == "📈 Báo cáo doanh thu":

    st.title(
        "📈 Báo cáo doanh thu"
    )

    bookings = fetch_bookings()

    if bookings.empty:

        st.info(
            "Chưa có dữ liệu doanh thu."
        )

    else:

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        total_revenue = bookings[
            "total_amount"
        ].fillna(0).sum()

        total_paid = bookings[
            "paid_amount"
        ].fillna(0).sum()

        total_debt = bookings[
            "remaining_amount"
        ].fillna(0).sum()

        total_bookings = len(
            bookings
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Tổng booking",
            total_bookings
        )

        col2.metric(
            "Doanh thu booking",
            format_money(total_revenue)
        )

        col3.metric(
            "Đã thu",
            format_money(total_paid)
        )

        col4.metric(
            "Còn phải thu",
            format_money(total_debt)
        )

        st.divider()

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        st.subheader(
            "📊 Booking theo trạng thái"
        )

        status_data = (
            bookings["status"]
            .value_counts()
            .reset_index()
        )

        status_data.columns = [
            "Trạng thái",
            "Số booking"
        ]

        st.bar_chart(
            status_data.set_index(
                "Trạng thái"
            )
        )

        st.divider()

        # ----------------------------------------------------
        # DAILY REVENUE
        # ----------------------------------------------------

        st.subheader(
            "💰 Doanh thu theo ngày nhận phòng"
        )

        bookings["check_in"] = pd.to_datetime(
            bookings["check_in"]
        )

        daily = (
            bookings
            .groupby(
                bookings["check_in"].dt.date
            )["total_amount"]
            .sum()
        )

        if not daily.empty:

            st.line_chart(
                daily
            )

        st.divider()

        st.subheader(
            "📋 Chi tiết doanh thu"
        )

        st.dataframe(
            bookings[
                [
                    "id",
                    "full_name",
                    "room_number",
                    "check_in",
                    "check_out",
                    "status",
                    "total_amount",
                    "paid_amount",
                    "remaining_amount"
                ]
            ],
            column_config={
                "id": "Booking",
                "full_name": "Khách",
                "room_number": "Phòng",
                "check_in": "Nhận",
                "check_out": "Trả",
                "status": "Trạng thái",
                "total_amount":
                    st.column_config.NumberColumn(
                        "Tổng tiền",
                        format="%,.0f VNĐ"
                    ),
                "paid_amount":
                    st.column_config.NumberColumn(
                        "Đã thu",
                        format="%,.0f VNĐ"
                    ),
                "remaining_amount":
                    st.column_config.NumberColumn(
                        "Còn lại",
                        format="%,.0f VNĐ"
                    )
            },
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "🏨 Hotel Manager"
)

st.sidebar.caption(
    "Streamlit + MySQL + Aiven"
)
