import { useEffect } from "react";
import { queryData } from "./services/api";

function App() {
    useEffect(() => {
        queryData({
            metric: "temperature",
            depth: 10,
        }).then((data) => {
            console.log("API response:", data);
        });
    }, []);

    return <div>Check console for API response</div>;
}

export default App;
