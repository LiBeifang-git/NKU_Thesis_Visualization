const express = require('express');
const cors = require('cors');
const mysql = require('mysql2/promise');

const app = express();
app.use(cors());
app.use(express.json());

const pool = mysql.createPool({
  host: '10.130.36.92',
  user: 'root',
  password: 'cjy20030306yuE',
  database: 'nk_thesis'
});

app.get('/api/cjy/midup', async (req, res) => {
  try {

      const [paperRows] = await pool.query('SELECT COUNT(*) AS total_papers FROM thesis_detail');
      const totalPapers = paperRows[0].total_papers;

      const [teacherRows] = await pool.query(`
      SELECT COUNT(DISTINCT CONCAT(\`第一导师姓名\`, '-', \`院系\`)) AS total_teachers
      FROM thesis_detail
      WHERE \`第一导师姓名\` IS NOT NULL AND \`第一导师姓名\` <> ''
    `);
      const totalTeachers = teacherRows[0].total_teachers;

      const [studentRows] = await pool.query(`
        SELECT COUNT(DISTINCT CONCAT(\`作者\`, '-', \`院系\`)) AS total_students
        FROM thesis_detail
        WHERE \`作者\` IS NOT NULL AND \`作者\` <> ''
      `);
      const totalStudents = studentRows[0].total_students;

      const [collegeRows] = await pool.query(`
        SELECT COUNT(DISTINCT \`院系\`) AS total_colleges
        FROM thesis_detail
        WHERE \`院系\` IS NOT NULL AND \`院系\` <> ''
      `);
      const totalColleges = collegeRows[0].total_colleges;

      res.json({
        total_papers: totalPapers,
        total_teachers: totalTeachers,
        total_students: totalStudents,
        total_colleges: totalColleges
      });
       
  } catch (err) {
      console.error(err);
      res.status(500).send('Database error');
  }
});



app.get('/api/cjy/rightup', async (req, res) => {
  try {

    const [rows] = await pool.query(`
      SELECT \`中文标题\` AS title,
             \`点击量\` AS views
      FROM thesis_detail
      ORDER BY \`点击量\` DESC
      LIMIT 8
    `);


    const maxView = rows.length ? rows[0].views : 1;

    const list = rows.map((item, index) => ({
      rank: index + 1,
      title: item.title,
      views: item.views,
      percent: ((item.views / maxView) * 100).toFixed(2) 
    }));

    res.json({ code: 200, data: list });
  } catch (err) {
    console.error(err);
    res.status(500).json({ code: 500, message: 'Server Error' });
  }
});


app.get('/api/cjy/rightdown', async (req, res) => {
  try {
    const [rows] = await pool.query( `
      SELECT 学位年度 AS year, 学生类型 AS level, COUNT(*) AS count
      FROM thesis_detail
      WHERE 学位年度 IN (2022, 2023, 2024)
        AND 学生类型 IN ('硕士', '博士')
      GROUP BY 学位年度, 学生类型
      ORDER BY 学位年度 DESC;
    `);

    const data = {
      "2024": { "硕士": 0, "博士": 0 },
      "2023": { "硕士": 0, "博士": 0 },
      "2022": { "硕士": 0, "博士": 0 }
    };

    rows.forEach(row => {
      if (data[row.year]) {
        data[row.year][row.level] = row.count;
      }
    });

    res.json({ code: 200, data });

  } catch (err) {
    console.error(err);
    res.status(500).json({ code: 500, message: "Server Error" });
  }
});

app.get('/api/cjy/leftdown', async (req, res) => {
  try {

     const [yearRows] = await pool.query(`
      SELECT 学位年度 AS year, COUNT(*) AS count
      FROM thesis_detail
      GROUP BY 学位年度
      ORDER BY count DESC
      LIMIT 1
    `);
    const top_year = yearRows[0] ? { year: String(yearRows[0].year), count: yearRows[0].count } : { year: null, count: 0 };

    const [phdRows] = await pool.query(`
      SELECT 院系 AS college,
             SUM(CASE WHEN 学生类型 = '博士' THEN 1 ELSE 0 END) AS phd_count,
             COUNT(*) AS total_count,
             SUM(CASE WHEN 学生类型 = '博士' THEN 1 ELSE 0 END) / COUNT(*) AS phd_ratio
      FROM thesis_detail
      GROUP BY 院系
      HAVING total_count > 0
      ORDER BY phd_ratio DESC
      LIMIT 1
    `);
    
    const top_phd_college = phdRows[0]
    ? {
        college: phdRows[0].college,
        phd_count: Number(phdRows[0].phd_count),
        total_count: Number(phdRows[0].total_count),
        phd_ratio: Number(phdRows[0].phd_ratio) 
      }
    : { college: null, phd_count: 0, total_count: 0, phd_ratio: 0 };

    const [teacherRows] = await pool.query(`
      SELECT 
          \`第一导师姓名\` AS teacher, 
          院系 AS college,
          COUNT(*) AS student_count
      FROM thesis_detail
      WHERE \`第一导师姓名\` IS NOT NULL AND \`第一导师姓名\` <> ''
      GROUP BY \`第一导师姓名\`, 院系
      ORDER BY student_count DESC
      LIMIT 1
    `);
    
    const top_teacher = teacherRows[0]
  ? { 
      teacher: teacherRows[0].teacher, 
      college: teacherRows[0].college,
      student_count: teacherRows[0].student_count 
    }
  : { teacher: null, college: null, student_count: 0 };

    const [collegeRows] = await pool.query(`
      SELECT 院系 AS college, COUNT(*) AS paper_count
      FROM thesis_detail
      GROUP BY 院系
      ORDER BY paper_count DESC
      LIMIT 1
    `);
    const top_college = collegeRows[0] ? { college: collegeRows[0].college, paper_count: collegeRows[0].paper_count } : { college: null, paper_count: 0 };

      const [[maxObj]] = await pool.query(
        `SELECT MAX(CAST(\`参考文献总数\` AS UNSIGNED)) AS max_refs FROM thesis_detail;`
      );
  
      const max_refs = Number(maxObj.max_refs);
      let top_reference = { max_refs: 0, students: [] };
  
      if (max_refs > 0) {
        const [refRows] = await pool.query(`
          SELECT 学号 AS student_id, 作者 AS name, \`参考文献总数\` AS refs
          FROM thesis_detail
          WHERE \`参考文献总数\` = ?
        `, [max_refs]);
  
        top_reference = {
          max_refs,
          students: refRows.map(r => ({
            id: r.student_id,
            name: r.name,
            refs: r.refs
          }))
        };
      }

    const [topDoctorCollege] = await pool.query(`
      SELECT 院系 AS college,
             COUNT(*) AS doctor_total
      FROM thesis_detail
      WHERE 学生类型 = '博士'
      GROUP BY 院系
      ORDER BY doctor_total DESC
      LIMIT 1;
    `);

    const top_doctor_college = topDoctorCollege[0]
    ? {
        college: topDoctorCollege[0].college,
        doctor_total: Number(topDoctorCollege[0].doctor_total)
      }
    : { college: null, doctor_total: 0 };


    res.json({
      code: 200,
      data: {
        top_year,
        top_phd_college,
        top_teacher,
        top_college,
        top_reference,
        top_doctor_college
      }
    });
    


  } catch (err) {
    console.error(err);
    res.status(500).json({ code: 500, message: "Server Error" });
  }
});


app.get('/api/cjy/middown', async (req, res) => {
  try {
    const [rows] = await pool.query(`
 SELECT
    学位年度 AS year,
    院系 AS college,
    AVG(CAST(\`参考文献总数\` AS UNSIGNED)) AS avg_refs,
    MAX(CAST(\`参考文献总数\`AS UNSIGNED)) AS max_refs,
    MIN(CAST(\`参考文献总数\`AS UNSIGNED)) AS min_refs,
    COUNT(*) AS thesis_count
FROM
    thesis_detail
WHERE
  \`参考文献总数\` IS NOT NULL
    AND \`参考文献总数\` <> ''
    AND 学位年度 >= 2004
    AND 院系 IN (
        '化学学院',
        '医学院',
        '历史学院',
        '商学院',
        '外国语学院',
        '数学科学学院',
        '文学院',
        '物理科学学院',
        '环境科学与工程学院',
        '生命科学学院',
        '经济学院'
    )
GROUP BY
    学位年度,
    院系
ORDER BY
    学位年度 ASC,
    avg_refs DESC;
    `);
    res.json(rows);
    
  } catch (err) {
    console.error(err);
    res.status(500).send('Server Error');
  }
});

app.get('/api/cjy/middown', async (req, res) => {
  try {
    const [rows] = await pool.query(`
 SELECT
    学位年度 AS year,
    院系 AS college,
    AVG(CAST(\`参考文献总数\` AS UNSIGNED)) AS avg_refs,
    MAX(CAST(\`参考文献总数\`AS UNSIGNED)) AS max_refs,
    MIN(CAST(\`参考文献总数\`AS UNSIGNED)) AS min_refs,
    COUNT(*) AS thesis_count
FROM
    thesis_detail
WHERE
  \`参考文献总数\` IS NOT NULL
    AND \`参考文献总数\` <> ''
    AND 学位年度 >= 2004
    AND 院系 IN (
        '化学学院',
        '医学院',
        '历史学院',
        '商学院',
        '外国语学院',
        '数学科学学院',
        '文学院',
        '物理科学学院',
        '环境科学与工程学院',
        '生命科学学院',
        '经济学院'
    )
GROUP BY
    学位年度,
    院系
ORDER BY
    学位年度 ASC,
    avg_refs DESC;
    `);
    res.json(rows);
    
  } catch (err) {
    console.error(err);
    res.status(500).send('Server Error');
  }
});

app.get('/api/cjy/stream-data', async (req, res) => {
    try {
        const sql = `
            SELECT 
                学位年度 as year, 
                院系 as college, 
                COUNT(*) as count 
            FROM thesis_detail 
            WHERE 学位年度 >= 2004 
            GROUP BY 学位年度, 院系 
            ORDER BY 学位年度 ASC
        `;

        const [results] = await pool.query(sql);

        res.json({ 
            code: 200, 
            data: results 
        });

    } catch (err) {
        console.error("Database Error:", err);
        res.status(500).json({ 
            code: 500, 
            message: 'Database query failed' 
        });
    }
});

const path = require('path');

app.use(express.static(path.join(__dirname, 'src')));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'src', 'index.html'));
});


app.listen(3020, () => {
  console.log('Node server running at http://localhost:3020');
});
