import { useState } from "react";
import { queryData } from "../services/api";

export default function Home() {
    const [data, setData] = useState(null);

    const handleClick = async () => {
        const result = await queryData({ metric: "temperature", depth: 10 });
        setData(result);
    };

    return (
        <div>
            <h1>CalCOFI Data Viewer</h1>
            <button onClick={handleClick}>Fetch Data</button>
            <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
    );
}
